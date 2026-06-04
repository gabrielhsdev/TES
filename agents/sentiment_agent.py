import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from groq import Groq
from dotenv import load_dotenv
from shared.jsonrpc import JSONRPCRequest, make_success_response, make_error_response
from shared.news_analysis import analyze_sentiment_locally

load_dotenv()

app = FastAPI(title="Agente de Sentimento")
client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None


def should_use_llm() -> bool:
    return os.getenv("AGENT_MODE", "local").lower() == "llm" and client is not None


@app.get("/health")
def health():
    return {"status": "ok", "agent": "sentiment", "mode": "llm" if should_use_llm() else "local"}


@app.post("/rpc")
def handle_rpc(request: JSONRPCRequest):
    if request.method != "analyze_sentiment":
        return make_error_response(-32601, "Method not found", request.id)

    text = request.params.get("text", "")
    if not text:
        return make_error_response(-32602, "Parâmetro 'text' obrigatório", request.id)

    if not should_use_llm():
        return make_success_response(analyze_sentiment_locally(text), request.id)

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        'Você é um agente de análise de sentimento. '
                        'Analise o tom da notícia e responda APENAS com JSON válido no formato:\n'
                        '{"sentimento": "positivo|neutro|negativo", "confianca": 0.0-1.0, '
                        '"justificativa": "breve explicação em uma frase"}'
                    ),
                },
                {
                    "role": "user",
                    "content": f"Analise o sentimento da seguinte notícia:\n\n{text}",
                },
            ],
            max_tokens=150,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()

        try:
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw.strip())
        except Exception:
            raw_lower = raw.lower()
            if "positivo" in raw_lower:
                sentimento = "positivo"
            elif "negativo" in raw_lower:
                sentimento = "negativo"
            else:
                sentimento = "neutro"
            result = {"sentimento": sentimento, "confianca": 0.7, "justificativa": raw[:120]}

        return make_success_response(result, request.id)
    except Exception:
        return make_success_response(analyze_sentiment_locally(text), request.id)
