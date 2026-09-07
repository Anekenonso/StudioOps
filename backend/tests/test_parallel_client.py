"""Parallel Search client: request contract, error handling, normalization."""

from __future__ import annotations

import json

import httpx
import pytest

from backend.tools.parallel_client import (
    ParallelClient,
    ParallelSearchError,
    canonicalize_url,
)


def transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def fast(client: ParallelClient) -> ParallelClient:
    """Remove retry backoff so retry paths run instantly."""
    client._backoff_base = 0.0
    return client


class TestCanonicalizeUrl:
    def test_strips_tracking_params_and_fragment(self):
        assert (
            canonicalize_url("https://variety.com/a?utm_source=x&id=7#top")
            == "https://variety.com/a?id=7"
        )

    def test_normalizes_scheme_host_and_trailing_slash(self):
        assert canonicalize_url("http://www.Variety.com/a/") == "https://variety.com/a"

    def test_treats_variants_of_the_same_page_as_equal(self):
        assert canonicalize_url("https://deadline.com/story?ref=twitter") == canonicalize_url(
            "http://www.deadline.com/story/#comments"
        )

    def test_does_not_raise_on_junk_input(self):
        assert isinstance(canonicalize_url("not a url"), str)


class TestSearchRequest:
    async def test_posts_the_documented_contract(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["headers"] = request.headers
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"search_id": "s1", "results": []})

        client = ParallelClient(api_key="k")
        async with httpx.AsyncClient(transport=transport(handler)) as http:
            await client.search("nollywood thrillers", objective="find comps", client=http)

        assert captured["url"] == "https://api.parallel.ai/v1beta/search"
        # Parallel authenticates with x-api-key, not a bearer token.
        assert captured["headers"]["x-api-key"] == "k"
        assert "authorization" not in {k.lower() for k in captured["headers"]}

        assert captured["body"]["search_queries"] == ["nollywood thrillers"]
        assert captured["body"]["objective"] == "find comps"
        assert captured["body"]["max_results"] == 6
        assert captured["body"]["max_chars_per_result"] == 1500

    async def test_objective_defaults_to_the_query(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"results": []})

        async with httpx.AsyncClient(transport=transport(handler)) as http:
            await ParallelClient(api_key="k").search("lagos crime drama", client=http)

        assert captured["body"]["objective"] == "lagos crime drama"

    def test_requires_an_api_key(self, monkeypatch):
        monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
        with pytest.raises(ParallelSearchError, match="PARALLEL_API_KEY"):
            ParallelClient()

    async def test_respects_base_url_override(self, monkeypatch):
        monkeypatch.setenv("PARALLEL_BASE_URL", "https://proxy.internal/")
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            return httpx.Response(200, json={"results": []})

        async with httpx.AsyncClient(transport=transport(handler)) as http:
            await ParallelClient(api_key="k").search("q", client=http)

        assert seen["url"] == "https://proxy.internal/v1beta/search"


class TestErrorHandling:
    async def test_auth_failure_raises_without_retrying(self):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(401, text="unauthorized")

        client = fast(ParallelClient(api_key="bad", max_retries=3))
        async with httpx.AsyncClient(transport=transport(handler)) as http:
            with pytest.raises(ParallelSearchError, match="PARALLEL_API_KEY"):
                await client.search("q", client=http)

        assert calls["n"] == 1

    async def test_error_message_never_leaks_the_key(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="forbidden")

        client = fast(ParallelClient(api_key="super-secret-value", max_retries=1))
        async with httpx.AsyncClient(transport=transport(handler)) as http:
            with pytest.raises(ParallelSearchError) as excinfo:
                await client.search("q", client=http)

        assert "super-secret-value" not in str(excinfo.value)

    async def test_retries_server_errors_then_succeeds(self):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            if calls["n"] < 3:
                return httpx.Response(503, text="unavailable")
            return httpx.Response(
                200,
                json={
                    "results": [
                        {"url": "https://variety.com/a", "title": "A", "excerpts": ["x" * 200]}
                    ]
                },
            )

        client = fast(ParallelClient(api_key="k", max_retries=3))
        async with httpx.AsyncClient(transport=transport(handler)) as http:
            results = await client.search("q", client=http)

        assert calls["n"] == 3
        assert len(results) == 1

    async def test_retries_rate_limits(self):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(429, text="slow down", headers={"retry-after": "0"})
            return httpx.Response(200, json={"results": []})

        client = fast(ParallelClient(api_key="k", max_retries=3))
        async with httpx.AsyncClient(transport=transport(handler)) as http:
            assert await client.search("q", client=http) == []
        assert calls["n"] == 2

    async def test_gives_up_after_max_retries(self):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(500, text="boom")

        client = fast(ParallelClient(api_key="k", max_retries=2))
        async with httpx.AsyncClient(transport=transport(handler)) as http:
            with pytest.raises(ParallelSearchError):
                await client.search("q", client=http)

        assert calls["n"] == 2

    async def test_bad_request_is_not_retried(self):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(422, text="invalid field")

        client = fast(ParallelClient(api_key="k", max_retries=3))
        async with httpx.AsyncClient(transport=transport(handler)) as http:
            with pytest.raises(ParallelSearchError):
                await client.search("q", client=http)

        assert calls["n"] == 1

    async def test_timeout_is_wrapped_in_a_domain_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("too slow", request=request)

        client = fast(ParallelClient(api_key="k", max_retries=1))
        async with httpx.AsyncClient(transport=transport(handler)) as http:
            with pytest.raises(ParallelSearchError, match="timeout"):
                await client.search("q", client=http)

    async def test_network_error_is_wrapped(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("dns failure", request=request)

        client = fast(ParallelClient(api_key="k", max_retries=1))
        async with httpx.AsyncClient(transport=transport(handler)) as http:
            with pytest.raises(ParallelSearchError, match="network error"):
                await client.search("q", client=http)

    async def test_malformed_json_body_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html>not json</html>")

        client = fast(ParallelClient(api_key="k"))
        async with httpx.AsyncClient(transport=transport(handler)) as http:
            with pytest.raises(ParallelSearchError, match="malformed"):
                await client.search("q", client=http)

    async def test_empty_results_is_not_an_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"search_id": "s", "results": []})

        client = fast(ParallelClient(api_key="k"))
        async with httpx.AsyncClient(transport=transport(handler)) as http:
            assert await client.search("q", client=http) == []


class TestNormalizeResults:
    def test_reads_the_excerpts_array(self):
        """Parallel returns page text in `excerpts`, not `snippet`.

        Reading the wrong field silently empties the corpus: every source
        arrives with no text and the synthesizer has nothing to reason over.
        """
        results = ParallelClient.normalize_results(
            [
                {
                    "url": "https://variety.com/a",
                    "title": "Nollywood surge",
                    "publish_date": "2026-01-04",
                    "excerpts": ["First excerpt.", "Second excerpt."],
                }
            ]
        )
        assert results[0]["snippet"] == "First excerpt. Second excerpt."
        assert results[0]["excerpts"] == ["First excerpt.", "Second excerpt."]
        assert results[0]["published_date"] == "2026-01-04"
        assert results[0]["publisher"] == "variety.com"

    def test_accepts_a_string_excerpt(self):
        results = ParallelClient.normalize_results(
            [{"url": "https://a.com/x", "excerpts": "just one"}]
        )
        assert results[0]["excerpts"] == ["just one"]

    def test_deduplicates_by_canonical_url(self):
        results = ParallelClient.normalize_results(
            [
                {"url": "https://variety.com/a?utm_source=x", "excerpts": ["one"]},
                {"url": "http://www.variety.com/a/", "excerpts": ["two"]},
            ]
        )
        assert len(results) == 1

    def test_skips_items_without_a_url(self):
        assert ParallelClient.normalize_results([{"title": "no url"}]) == []

    def test_falls_back_to_the_domain_when_the_title_is_a_url(self):
        results = ParallelClient.normalize_results(
            [{"url": "https://guardian.ng/story", "title": "https://guardian.ng/story"}]
        )
        assert results[0]["title"] == "guardian.ng"

    def test_tolerates_non_dict_items(self):
        results = ParallelClient.normalize_results(
            ["junk", None, {"url": "https://a.com/x"}]
        )
        assert len(results) == 1
        assert results[0]["snippet"] == ""
