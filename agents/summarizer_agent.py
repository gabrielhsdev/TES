import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from groq import Groq
from dotenv import load_dotenv
from shared.jsonrpc import JSONRPCRequest, make_success_response, make_error_response
from shared.news_analysis import summarize_locally

load_dotenv()

app = FastAPI(title="Agente Resumidor")
client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None


def should_use_llm() -> bool:
    return os.getenv("AGENT_MODE", "local").lower() == "llm" and client is not None


@app.get("/health")
def health():
    return {"status": "ok", "agent": "summarizer", "mode": "llm" if should_use_llm() else "local"}


@app.post("/rpc")
def handle_rpc(request: JSONRPCRequest):
    if request.method != "summarize":
        return make_error_response(-32601, "Method not found", request.id)

    text = request.params.get("text", "")
    if not text:
        return make_error_response(-32602, "Parâmetro 'text' obrigatório", request.id)

    if not should_use_llm():
        return make_success_response({"summary": summarize_locally(text), "mode": "local"}, request.id)

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
    except Exception:
        return make_success_response({"summary": summarize_locally(text), "mode": "fallback_local"}, request.id)
