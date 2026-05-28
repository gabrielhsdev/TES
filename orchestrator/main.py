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


@app.get("/health")
def health():
    return {"status": "ok", "service": "orchestrator"}


@app.post("/analyze")
def analyze(body: AnalyzeRequest):
    from extractor import extract_article

    results = []

    with httpx.Client() as http:
        for url in body.urls:
            item: dict = {"url": url, "latencia": {}}

            t0 = time.perf_counter()
            article = extract_article(url)
            item["latencia"]["extrator_s"] = round(time.perf_counter() - t0, 3)
            item["titulo"] = article.get("title")

            if article.get("error") or not article.get("text"):
                item["erro"] = article.get("error", "Não foi possível extrair conteúdo")
                results.append(item)
                continue

            text = article["text"]

            try:
                resp, lat = call_agent(http, SUMMARIZER_URL, "summarize", text)
                item["latencia"]["resumidor_s"] = lat
                item["resumo"] = resp.get("result", {}).get("summary") if not resp.get("error") else None
            except Exception as e:
                item["resumo"] = None
                item["latencia"]["resumidor_s"] = -1

            try:
                resp, lat = call_agent(http, SENTIMENT_URL, "analyze_sentiment", text)
                item["latencia"]["sentimento_s"] = lat
                item["sentimento"] = resp.get("result") if not resp.get("error") else None
            except Exception as e:
                item["sentimento"] = None
                item["latencia"]["sentimento_s"] = -1

            try:
                resp, lat = call_agent(http, CATEGORIZER_URL, "categorize", text)
                item["latencia"]["categorizador_s"] = lat
                item["categoria"] = resp.get("result") if not resp.get("error") else None
            except Exception as e:
                item["categoria"] = None
                item["latencia"]["categorizador_s"] = -1

            item["latencia"]["total_s"] = round(
                sum(v for v in item["latencia"].values() if isinstance(v, float) and v >= 0), 3
            )
            results.append(item)

    report = {
        "id": str(uuid.uuid4()),
        "total_urls": len(body.urls),
        "resultados": results,
    }

    os.makedirs("reports", exist_ok=True)
    report_path = f"reports/report_{report['id'][:8]}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    report["arquivo"] = report_path
    return report
