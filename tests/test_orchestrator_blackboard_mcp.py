import json
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("GROQ_API_KEY", "test-key")

import mcp_server
from orchestrator import main as orchestrator
from shared.blackboard import Blackboard


class BlackboardTest(unittest.TestCase):
    def test_blackboard_records_and_persists_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            blackboard = Blackboard("run-12345678", reports_dir=tmp)
            blackboard.record("https://exemplo.test/noticia", "extrator", "concluido", {"latencia_s": 0.1})

            path = blackboard.save()

            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as file:
                data = json.load(file)
            self.assertEqual(data["total_events"], 1)
            self.assertEqual(data["events"][0]["stage"], "extrator")


class OrchestratorFlowTest(unittest.TestCase):
    def test_analyze_consolidates_results_report_and_blackboard(self):
        def fake_extract(url):
            if "erro" in url:
                return {"url": url, "title": None, "text": None, "error": "Falha simulada"}
            return {"url": url, "title": "Titulo", "text": "Texto da noticia", "error": None}

        def fake_call_agent(_client, _base_url, method, _text):
            payloads = {
                "summarize": {"result": {"summary": "Resumo"}},
                "analyze_sentiment": {
                    "result": {"sentimento": "neutro", "confianca": 0.9, "justificativa": "Informativo"}
                },
                "categorize": {"result": {"categoria": "tecnologia", "confianca": 0.8}},
            }
            return payloads[method], 0.01

        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                with patch("extractor.extract_article", fake_extract), patch(
                    "orchestrator.main.call_agent", fake_call_agent
                ):
                    report = orchestrator.analyze(
                        orchestrator.AnalyzeRequest(
                            urls=["https://exemplo.test/noticia", "https://exemplo.test/erro"]
                        )
                    )
            finally:
                os.chdir(old_cwd)

            self.assertEqual(report["total_urls"], 2)
            self.assertEqual(report["resultados"][0]["resumo"], "Resumo")
            self.assertEqual(report["resultados"][0]["sentimento"]["sentimento"], "neutro")
            self.assertEqual(report["resultados"][0]["categoria"]["categoria"], "tecnologia")
            self.assertEqual(report["resultados"][1]["erro"], "Falha simulada")
            self.assertTrue(os.path.exists(os.path.join(tmp, report["arquivo"])))
            self.assertTrue(os.path.exists(os.path.join(tmp, report["blackboard"])))


class McpServerTest(unittest.TestCase):
    def test_mcp_resources_tools_and_prompt_are_callable(self):
        self.assertIn("JSON-RPC 2.0", mcp_server.architecture())
        self.assertIn("reports", mcp_server.reports_index())
        self.assertIn("MCP", mcp_server.demo_script("professor"))
        self.assertEqual(mcp_server.latest_report()["error"], "Nenhum relatório encontrado em reports/.")


if __name__ == "__main__":
    unittest.main()
