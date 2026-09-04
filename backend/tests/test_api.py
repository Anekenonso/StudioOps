from fastapi.testclient import TestClient
import backend.api.routes as routes
from backend.main import app


def test_api_research_endpoint_monkeypatch(monkeypatch):
    # Monkeypatch GeminiClient.plan and synthesize to avoid external calls
    class DummyGemini:
        def __init__(self, *args, **kwargs):
            pass

        async def plan(self, brief):
            return {"research_tasks": [{"id": "q1", "query": "test q1"}]}

        async def synthesize(self, brief, evidence):
            # return a simple dict-like object
            return {"executive_summary": "stub", "sources": []}

    monkeypatch.setattr(routes, "GeminiClient", DummyGemini)

    # Monkeypatch ParallelClient to avoid network
    class DummyParallelClient:
        def __init__(self, *args, **kwargs):
            pass

        async def search(self, q):
            return [{"title": "T1", "url": "http://a", "snippet": "s", "source": "S1", "relevance": 0.9}]

    monkeypatch.setattr(routes, "ParallelClient", DummyParallelClient)

    client = TestClient(app)
    payload = {"title": "T", "description": "d"}
    res = client.post("/api/v1/research", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert "report" in data
