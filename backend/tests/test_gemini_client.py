"""Gemini adapter: credential detection, JSON extraction, error wrapping.

Gemini credentials arrive at deployment time, so the code path that matters most
before then is the unconfigured one: it must refuse cleanly, explain itself, and
never let callers mistake fallback output for model analysis.
"""

from __future__ import annotations

import pytest

from backend.integrations.gemini_client import (
    DEFAULT_MODEL,
    GeminiClient,
    GeminiError,
    GeminiStatus,
)


class TestCredentialDetection:
    def test_unconfigured_with_no_credentials(self):
        client = GeminiClient()

        assert client.configured is False
        assert client.status.mode == "unconfigured"
        assert "GEMINI_API_KEY" in client.status.detail

    def test_api_key_mode(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        status = GeminiClient().status

        assert status.configured is True
        assert status.mode == "api_key"

    def test_google_api_key_is_accepted(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        assert GeminiClient().status.mode == "api_key"

    def test_explicit_vertex_flag(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "studioops-demo")
        status = GeminiClient().status

        assert status.configured is True
        assert status.mode == "vertex"
        assert "studioops-demo" in status.detail

    def test_vertex_without_a_project_is_unconfigured(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
        status = GeminiClient().status

        assert status.configured is False
        assert "GOOGLE_CLOUD_PROJECT" in status.detail

    def test_project_plus_service_account_implies_vertex(self, monkeypatch, tmp_path):
        """Cloud Run mounts a service account; no API key will be present."""
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "studioops-demo")
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(tmp_path / "sa.json"))

        assert GeminiClient().status.mode == "vertex"

    def test_a_project_alone_does_not_imply_vertex(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "studioops-demo")
        assert GeminiClient().status.configured is False

    def test_an_api_key_wins_over_a_bare_project(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "studioops-demo")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        assert GeminiClient().status.mode == "api_key"

    def test_vertex_flag_accepts_common_truthy_spellings(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "p")
        for value in ("1", "true", "TRUE", "yes", "on"):
            monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", value)
            assert GeminiClient().status.mode == "vertex", value

    def test_vertex_flag_ignores_falsey_spellings(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "p")
        for value in ("0", "false", "no", ""):
            monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", value)
            assert GeminiClient().status.configured is False, value

    def test_defaults_the_model_and_location(self):
        client = GeminiClient()
        assert client.model == DEFAULT_MODEL
        assert client.location == "us-central1"

    def test_model_is_configurable(self, monkeypatch):
        monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
        assert GeminiClient().model == "gemini-2.5-pro"

    def test_constructor_arguments_override_the_environment(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        client = GeminiClient(model="gemini-2.5-pro", api_key="arg-key")

        assert client.model == "gemini-2.5-pro"
        assert client.api_key == "arg-key"


class TestStatusReporting:
    def test_status_dict_carries_no_key_material(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "super-secret-key")
        payload = GeminiClient().status.as_dict()

        assert set(payload) == {"configured", "mode", "model", "detail"}
        assert "super-secret-key" not in str(payload)

    def test_status_dict_is_json_safe(self):
        import json

        json.dumps(GeminiClient().status.as_dict())


class TestGenerateJson:
    async def test_refuses_when_unconfigured(self):
        """Callers must get a clear error, never silent fake output."""
        with pytest.raises(GeminiError, match="not configured"):
            await GeminiClient().generate_json("system", "prompt")

    async def test_parses_a_plain_json_response(self, monkeypatch):
        client = _stub_client(monkeypatch, '{"tasks": [1, 2]}')
        assert await client.generate_json("s", "p") == {"tasks": [1, 2]}

    async def test_parses_a_fenced_json_response(self, monkeypatch):
        client = _stub_client(monkeypatch, '```json\n{"ok": true}\n```')
        assert await client.generate_json("s", "p") == {"ok": True}

    async def test_raises_on_an_empty_response(self, monkeypatch):
        client = _stub_client(monkeypatch, "")
        with pytest.raises(GeminiError, match="empty"):
            await client.generate_json("s", "p")

    async def test_raises_on_unparseable_output(self, monkeypatch):
        client = _stub_client(monkeypatch, "I'm afraid I can't do that.")
        with pytest.raises(GeminiError, match="unparseable"):
            await client.generate_json("s", "p")

    async def test_wraps_an_sdk_exception(self, monkeypatch):
        client = _stub_client(monkeypatch, "", raise_error=RuntimeError("quota exceeded"))
        with pytest.raises(GeminiError, match="failed"):
            await client.generate_json("s", "p")

    async def test_retries_once_without_the_schema(self, monkeypatch):
        """Some model/schema combinations are rejected server-side; the JSON
        mime type plus the schema in the system instruction still works."""
        calls = []

        def generate(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise RuntimeError("response_schema not supported")
            return _FakeResponse('{"ok": true}')

        client = _stub_client(monkeypatch, "", generate=generate)
        result = await client.generate_json("s", "p", response_schema={"type": "object"})

        assert result == {"ok": True}
        assert len(calls) == 2

    async def test_a_schemaless_failure_is_not_retried(self, monkeypatch):
        calls = []

        def generate(**kwargs):
            calls.append(kwargs)
            raise RuntimeError("hard failure")

        client = _stub_client(monkeypatch, "", generate=generate)
        with pytest.raises(GeminiError):
            await client.generate_json("s", "p")

        assert len(calls) == 1

    async def test_timeout_is_wrapped(self, monkeypatch):
        import time

        def slow(**_kwargs):
            time.sleep(0.5)
            return _FakeResponse("{}")

        client = _stub_client(monkeypatch, "", generate=slow)
        with pytest.raises(GeminiError, match="timed out"):
            await client.generate_json("s", "p", timeout=0.05)

    async def test_passes_generation_settings_through(self, monkeypatch):
        calls = []

        def generate(**kwargs):
            calls.append(kwargs)
            return _FakeResponse("{}")

        client = _stub_client(monkeypatch, "", generate=generate)
        await client.generate_json(
            "the system instruction", "the prompt", temperature=0.4, max_output_tokens=1024
        )

        config = calls[0]["config"]
        assert calls[0]["contents"] == "the prompt"
        assert config.system_instruction == "the system instruction"
        assert config.temperature == 0.4
        assert config.max_output_tokens == 1024
        assert config.response_mime_type == "application/json"


class TestExtractText:
    def test_prefers_the_response_text_property(self):
        assert GeminiClient._extract_text(_FakeResponse("hello")) == "hello"

    def test_falls_back_to_candidate_parts(self):
        """`response.text` is empty when output is split across parts."""
        response = _FakeResponse("", parts=["part one", "part two"])
        assert GeminiClient._extract_text(response) == "part one\npart two"

    def test_returns_empty_for_an_unrecognized_shape(self):
        assert GeminiClient._extract_text(object()) == ""

    def test_ignores_blank_parts(self):
        response = _FakeResponse("", parts=["", "   ", "real"])
        assert GeminiClient._extract_text(response) == "real"


class _FakeResponse:
    """Minimal stand-in for a GenerateContentResponse."""

    def __init__(self, text: str, parts: list[str] | None = None) -> None:
        self.text = text
        if parts is None:
            self.candidates = []
        else:
            part_objects = [type("Part", (), {"text": p})() for p in parts]
            content = type("Content", (), {"parts": part_objects})()
            self.candidates = [type("Candidate", (), {"content": content})()]


def _stub_client(monkeypatch, text: str, raise_error=None, generate=None) -> GeminiClient:
    """A configured GeminiClient whose SDK call is replaced by a local stub."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = GeminiClient()

    def default_generate(**_kwargs):
        if raise_error is not None:
            raise raise_error
        return _FakeResponse(text)

    call = generate or default_generate
    models = type("Models", (), {"generate_content": staticmethod(call)})()
    client._client = type("Client", (), {"models": models})()
    return client
