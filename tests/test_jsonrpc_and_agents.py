import json
import os
import unittest

os.environ.setdefault("GROQ_API_KEY", "test-key")

from agents import categorizer_agent, sentiment_agent, summarizer_agent
from shared.jsonrpc import JSONRPCRequest, make_error_response, make_success_response


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _Message(content)


class _GroqResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_Choice(content)]


class _FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content

    def create(self, **_kwargs):
        return _GroqResponse(self.content)


class _FakeChat:
    def __init__(self, content: str) -> None:
        self.completions = _FakeCompletions(content)


class _FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = _FakeChat(content)


class JsonRpcContractTest(unittest.TestCase):
    def test_success_response_preserves_jsonrpc_and_id(self):
        response = make_success_response({"ok": True}, "abc")

        self.assertEqual(response.jsonrpc, "2.0")
        self.assertEqual(response.id, "abc")
        self.assertEqual(response.result, {"ok": True})
        self.assertIsNone(response.error)

    def test_error_response_preserves_jsonrpc_and_id(self):
        response = make_error_response(-32601, "Method not found", "abc")

        self.assertEqual(response.jsonrpc, "2.0")
        self.assertEqual(response.id, "abc")
        self.assertEqual(response.error.code, -32601)
        self.assertIsNone(response.result)


class AgentValidationTest(unittest.TestCase):
    def tearDown(self):
        os.environ["AGENT_MODE"] = "local"

    def test_agents_reject_unknown_method(self):
        request = JSONRPCRequest(method="unknown", params={"text": "noticia"}, id="1")

        for module in [summarizer_agent, sentiment_agent, categorizer_agent]:
            with self.subTest(agent=module.__name__):
                response = module.handle_rpc(request)
                self.assertEqual(response.error.code, -32601)

    def test_agents_reject_missing_text(self):
        requests = [
            (summarizer_agent, JSONRPCRequest(method="summarize", params={}, id="1")),
            (sentiment_agent, JSONRPCRequest(method="analyze_sentiment", params={}, id="2")),
            (categorizer_agent, JSONRPCRequest(method="categorize", params={}, id="3")),
        ]

        for module, request in requests:
            with self.subTest(agent=module.__name__):
                response = module.handle_rpc(request)
                self.assertEqual(response.error.code, -32602)

    def test_agents_return_structured_success_with_mocked_llm(self):
        os.environ["AGENT_MODE"] = "llm"
        summarizer_agent.client = _FakeClient("Resumo curto em tres frases.")
        sentiment_agent.client = _FakeClient(
            json.dumps({"sentimento": "neutro", "confianca": 0.9, "justificativa": "Tom informativo."})
        )
        categorizer_agent.client = _FakeClient(json.dumps({"categoria": "tecnologia", "confianca": 0.8}))

        summary = summarizer_agent.handle_rpc(JSONRPCRequest(method="summarize", params={"text": "texto"}, id="1"))
        sentiment = sentiment_agent.handle_rpc(
            JSONRPCRequest(method="analyze_sentiment", params={"text": "texto"}, id="2")
        )
        category = categorizer_agent.handle_rpc(JSONRPCRequest(method="categorize", params={"text": "texto"}, id="3"))

        self.assertEqual(summary.result["summary"], "Resumo curto em tres frases.")
        self.assertEqual(sentiment.result["sentimento"], "neutro")
        self.assertEqual(category.result["categoria"], "tecnologia")

    def test_agents_work_locally_without_consuming_llm_api(self):
        os.environ["AGENT_MODE"] = "local"
        text = "A tecnologia melhora processos e gera avanço positivo para empresas."

        summary = summarizer_agent.handle_rpc(JSONRPCRequest(method="summarize", params={"text": text}, id="1"))
        sentiment = sentiment_agent.handle_rpc(
            JSONRPCRequest(method="analyze_sentiment", params={"text": text}, id="2")
        )
        category = categorizer_agent.handle_rpc(JSONRPCRequest(method="categorize", params={"text": text}, id="3"))

        self.assertEqual(summary.result["mode"], "local")
        self.assertEqual(sentiment.result["sentimento"], "positivo")
        self.assertEqual(category.result["categoria"], "tecnologia")


if __name__ == "__main__":
    unittest.main()
