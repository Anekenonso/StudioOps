import asyncio
import types
import pytest

from backend.tools.parallel_client import ParallelClient


class DummyResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data


class DummyAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        return DummyResponse({"results": [{"title": "T1", "url": "http://a", "snippet": "s", "source": "S1", "score": 0.9}]})


def test_parallel_client_search_monkeypatch(monkeypatch):
    # Patch httpx.AsyncClient to our dummy
    import backend.tools.parallel_client as pcmod

    monkeypatch.setattr(pcmod, "httpx", types.SimpleNamespace(AsyncClient=DummyAsyncClient))

    client = ParallelClient(api_key="key", base_url="https://example.com")
    results = asyncio.run(client.search("test query"))
    assert isinstance(results, list)
    assert results[0]["url"] == "http://a"
