import glob
import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from orchestrator.main import AnalyzeRequest, analyze


mcp = FastMCP("Grupo 5 News MAS", json_response=True)


def _load_json(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def _report_paths() -> list[str]:
    return sorted(glob.glob(os.path.join("reports", "report_*.json")), reverse=True)


@mcp.resource("news://architecture")
def architecture() -> str:
    """Descreve a arquitetura multi-agente exposta para clientes MCP."""
    return (
        "Pipeline de análise de notícias do Grupo 5: um orquestrador FastAPI recebe URLs, "
        "extrai conteúdo e chama três agentes independentes por JSON-RPC 2.0 "
        "(resumidor, sentimento e categorizador). Os resultados são consolidados em JSON, "
        "com latência por etapa e blackboard de eventos intermediários."
    )


@mcp.resource("news://reports")
def reports_index() -> str:
    """Lista relatórios JSON gerados pelo pipeline."""
    reports = [{"path": path, "name": os.path.basename(path)} for path in _report_paths()]
    return json.dumps({"total": len(reports), "reports": reports}, ensure_ascii=False, indent=2)


@mcp.tool()
def analyze_urls(urls: list[str]) -> dict[str, Any]:
    """Executa o pipeline multi-agente para uma lista de URLs de notícias."""
    return analyze(AnalyzeRequest(urls=urls))


@mcp.tool()
def latest_report() -> dict[str, Any]:
    """Retorna o relatório mais recente gerado pelo orquestrador."""
    reports = _report_paths()
    if not reports:
        return {"error": "Nenhum relatório encontrado em reports/."}
    return _load_json(reports[0])


@mcp.prompt()
def demo_script(audience: str = "professor") -> str:
    """Gera um roteiro curto para apresentar a demo do projeto."""
    return (
        f"Explique para {audience} como o orquestrador recebe URLs, distribui tarefas por "
        "JSON-RPC 2.0 para agentes especializados, registra latência e blackboard, "
        "e expõe resultados em relatório JSON, Streamlit e MCP."
    )


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)
