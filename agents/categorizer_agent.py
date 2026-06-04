import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from groq import Groq
from dotenv import load_dotenv
from shared.jsonrpc import JSONRPCRequest, make_success_response, make_error_response
from shared.news_analysis import CATEGORIES, categorize_locally

load_dotenv()

app = FastAPI(title="Agente Categorizador")
client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None


def should_use_llm() -> bool:
    return os.getenv("AGENT_MODE", "local").lower() == "llm" and client is not None


@app.get("/health")
def health():
    return {"status": "ok", "agent": "categorizer", "mode": "llm" if should_use_llm() else "local"}


@app.post("/rpc")
def handle_rpc(request: JSONRPCRequest):
    if request.method != "categorize":
        return make_error_response(-32601, "Method not found", request.id)

    text = request.params.get("text", "")
    if not text:
        return make_error_response(-32602, "Parâmetro 'text' obrigatório", request.id)

    if not should_use_llm():
        return make_success_response(categorize_locally(text), request.id)

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Você é um agente categorizador de notícias. "
                        f"Categorize a notícia em UMA das seguintes categorias: {', '.join(CATEGORIES)}. "
                        f'Responda APENAS com JSON válido no formato:\n'
                        f'{{"categoria": "nome_da_categoria", "confianca": 0.0-1.0}}'
                    ),
                },
                {
                    "role": "user",
                    "content": f"Categorize a seguinte notícia:\n\n{text}",
                },
            ],
            max_tokens=80,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()

        try:
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw.strip())
        except Exception:
            raw_lower = raw.lower()
            categoria = "outro"
            for cat in CATEGORIES:
                if cat in raw_lower:
                    categoria = cat
                    break
            result = {"categoria": categoria, "confianca": 0.7}

        return make_success_response(result, request.id)
    except Exception:
        return make_success_response(categorize_locally(text), request.id)
