import os
import sys
import json
import uuid
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import httpx
from dotenv import load_dotenv
from shared.jsonrpc import JSONRPCRequest
from shared.blackboard import Blackboard

load_dotenv()

app = FastAPI(title="Orquestrador de Notícias")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUMMARIZER_URL = os.getenv("SUMMARIZER_URL", "http://localhost:8001")
SENTIMENT_URL = os.getenv("SENTIMENT_URL", "http://localhost:8002")
CATEGORIZER_URL = os.getenv("CATEGORIZER_URL", "http://localhost:8003")


class AnalyzeRequest(BaseModel):
    urls: List[str]


def call_agent(client: httpx.Client, base_url: str, method: str, text: str) -> tuple[dict, float]:
    request = JSONRPCRequest(method=method, params={"text": text})
    start = time.perf_counter()
    response = client.post(f"{base_url}/rpc", json=request.model_dump(), timeout=60.0)
    elapsed = round(time.perf_counter() - start, 3)
    return response.json(), elapsed


AGENT_STEPS = [
    (
        "resumidor",
        "resumidor_s",
        SUMMARIZER_URL,
        "summarize",
        "resumo",
        lambda response: response.get("result", {}).get("summary"),
    ),
    (
        "sentimento",
        "sentimento_s",
        SENTIMENT_URL,
        "analyze_sentiment",
        "sentimento",
        lambda response: response.get("result"),
    ),
    (
        "categorizador",
        "categorizador_s",
        CATEGORIZER_URL,
        "categorize",
        "categoria",
        lambda response: response.get("result"),
    ),
]


@app.get("/health")
def health():
    return {"status": "ok", "service": "orchestrator"}


@app.post("/analyze")
def analyze(body: AnalyzeRequest):
    from extractor import extract_article

    run_id = str(uuid.uuid4())
    blackboard = Blackboard(run_id)
    results = []

    with httpx.Client() as http:
        for url in body.urls:
            item: dict = {"url": url, "latencia": {}}
            blackboard.record(url, "recebimento", "iniciado", {"url": url})

            t0 = time.perf_counter()
            article = extract_article(url)
            item["latencia"]["extrator_s"] = round(time.perf_counter() - t0, 3)
            item["titulo"] = article.get("title")
            blackboard.record(
                url,
                "extrator",
                "erro" if article.get("error") or not article.get("text") else "concluido",
                {
                    "titulo": item["titulo"],
                    "latencia_s": item["latencia"]["extrator_s"],
                    "erro": article.get("error"),
                },
            )

            if article.get("error") or not article.get("text"):
                item["erro"] = article.get("error", "Não foi possível extrair conteúdo")
                blackboard.record(url, "url", "finalizado_com_erro", {"erro": item["erro"]})
                results.append(item)
                continue

            text = article["text"]
            item["erros_agentes"] = {}

            for stage, latency_key, base_url, method, result_key, extract_result in AGENT_STEPS:
                try:
                    resp, lat = call_agent(http, base_url, method, text)
                    item["latencia"][latency_key] = lat
                    if resp.get("error"):
                        item[result_key] = None
                        item["erros_agentes"][stage] = resp["error"].get("message", "Erro no agente")
                        status = "erro"
                    else:
                        item[result_key] = extract_result(resp)
                        status = "concluido" if item[result_key] is not None else "erro"
                    blackboard.record(url, stage, status, {"latencia_s": lat, "resultado": item[result_key]})
                except Exception as e:
                    item[result_key] = None
                    item["latencia"][latency_key] = -1
                    item["erros_agentes"][stage] = str(e)
                    blackboard.record(url, stage, "erro", {"erro": str(e), "resultado": item[result_key]})

            if not item["erros_agentes"]:
                del item["erros_agentes"]

            item["latencia"]["total_s"] = round(
                sum(v for v in item["latencia"].values() if isinstance(v, float) and v >= 0), 3
            )
            blackboard.record(url, "url", "finalizado", {"latencia_total_s": item["latencia"]["total_s"]})
            results.append(item)

    report = {
        "id": run_id,
        "total_urls": len(body.urls),
        "resultados": results,
    }

    os.makedirs("reports", exist_ok=True)
    report_path = f"reports/report_{report['id'][:8]}.json"
    report["arquivo"] = report_path
    report["blackboard"] = blackboard.save()

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report
