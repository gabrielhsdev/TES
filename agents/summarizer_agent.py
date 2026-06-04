import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from dotenv import load_dotenv
from shared.jsonrpc import JSONRPCRequest, make_success_response, make_error_response
from shared.news_analysis import summarize_locally

try:
    from groq import Groq
except ImportError:
    Groq = None

load_dotenv()

app = FastAPI(title="Agente Resumidor")
client = Groq(api_key=os.getenv("GROQ_API_KEY")) if Groq and os.getenv("GROQ_API_KEY") else None


def use_local_mode() -> bool:
    return os.getenv("AGENT_MODE", "llm").lower() == "local"


def should_use_llm() -> bool:
    return not use_local_mode() and client is not None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "agent": "summarizer",
        "mode": "local" if use_local_mode() else "llm",
        "ready": use_local_mode() or client is not None,
    }


@app.post("/rpc")
def handle_rpc(request: JSONRPCRequest):
    if request.method != "summarize":
        return make_error_response(-32601, "Method not found", request.id)

    text = request.params.get("text", "")
    if not text:
        return make_error_response(-32602, "Parâmetro 'text' obrigatório", request.id)

    if use_local_mode():
        return make_success_response({"summary": summarize_locally(text), "mode": "local"}, request.id)

    if not should_use_llm():
        return make_error_response(-32603, "Configure GROQ_API_KEY ou use AGENT_MODE=local", request.id)

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um agente resumidor de notícias. "
                        "Gere um resumo conciso em português com no máximo 3 frases. "
                        "Seja direto e objetivo."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Resuma a seguinte notícia:\n\n{text}",
                },
            ],
            max_tokens=250,
            temperature=0.3,
        )
        summary = response.choices[0].message.content.strip()
        return make_success_response({"summary": summary, "mode": "llm"}, request.id)
    except Exception as e:
        return make_error_response(-32603, str(e), request.id)
