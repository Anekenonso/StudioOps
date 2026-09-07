"""Gemini adapter built on the current `google-genai` SDK.

Supports both auth paths the hackathon environment may provide:

  Vertex AI (Google Cloud, service account / ADC):
      GOOGLE_GENAI_USE_VERTEXAI=true
      GOOGLE_CLOUD_PROJECT=<project-id>
      GOOGLE_CLOUD_LOCATION=us-central1
      GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json

  Gemini Developer API (API key):
      GEMINI_API_KEY=<key>            (or GOOGLE_API_KEY)

  Model selection:
      GEMINI_MODEL=gemini-2.5-pro     (defaults to gemini-2.5-flash)

The previous implementation targeted `TextGenerationModel` from
`google-cloud-aiplatform`, which is the retired PaLM-era API and never
resolved — every call fell through to a local stub. This adapter calls
`client.models.generate_content` with a response schema so the model returns
validated JSON.

`configured` reports whether real Gemini calls are possible. When it is False,
callers fall back to the deterministic planner/synthesizer, and the report
records `generated_by="fallback"` so the output is never passed off as
model-generated analysis.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"

try:  # pragma: no cover - import guard
    from google import genai
    from google.genai import types as genai_types

    _SDK_AVAILABLE = True
    _SDK_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - import guard
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]
    _SDK_AVAILABLE = False
    _SDK_IMPORT_ERROR = str(exc)


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


@dataclass
class GeminiStatus:
    """Why Gemini is or isn't usable — surfaced in run metadata and /health."""

    configured: bool
    mode: str  # "vertex" | "api_key" | "unconfigured"
    model: str
    detail: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "configured": self.configured,
            "mode": self.mode,
            "model": self.model,
            "detail": self.detail,
        }


class GeminiError(RuntimeError):
    """Raised when a Gemini call fails or returns unusable output."""


class GeminiClient:
    """Thin async wrapper over `google-genai` structured generation."""

    def __init__(
        self,
        project: Optional[str] = None,
        location: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        use_vertex: Optional[bool] = None,
    ) -> None:
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"
        self.model = model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if use_vertex is None:
            use_vertex = _truthy(os.getenv("GOOGLE_GENAI_USE_VERTEXAI"))
            # A project plus credentials with no API key implies Vertex.
            if not use_vertex and not self.api_key and self.project:
                use_vertex = bool(
                    os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                    or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
                )
        self.use_vertex = bool(use_vertex)

        self._client: Optional[Any] = None
        self._status = self._build_client()

    @property
    def status(self) -> GeminiStatus:
        return self._status

    @property
    def configured(self) -> bool:
        return self._status.configured

    def _build_client(self) -> GeminiStatus:
        if not _SDK_AVAILABLE:
            return GeminiStatus(
                configured=False,
                mode="unconfigured",
                model=self.model,
                detail=f"google-genai not importable: {_SDK_IMPORT_ERROR}",
            )

        try:
            if self.use_vertex:
                if not self.project:
                    return GeminiStatus(
                        configured=False,
                        mode="unconfigured",
                        model=self.model,
                        detail="Vertex mode requested but GOOGLE_CLOUD_PROJECT is not set.",
                    )
                self._client = genai.Client(
                    vertexai=True, project=self.project, location=self.location
                )
                return GeminiStatus(
                    configured=True,
                    mode="vertex",
                    model=self.model,
                    detail=f"Vertex AI project={self.project} location={self.location}",
                )

            if self.api_key:
                self._client = genai.Client(api_key=self.api_key)
                return GeminiStatus(
                    configured=True,
                    mode="api_key",
                    model=self.model,
                    detail="Gemini Developer API",
                )

            return GeminiStatus(
                configured=False,
                mode="unconfigured",
                model=self.model,
                detail=(
                    "No Gemini credentials. Set GEMINI_API_KEY, or "
                    "GOOGLE_GENAI_USE_VERTEXAI=true with GOOGLE_CLOUD_PROJECT."
                ),
            )
        except Exception as exc:
            logger.warning("gemini.init_failed: %s", exc)
            return GeminiStatus(
                configured=False,
                mode="unconfigured",
                model=self.model,
                detail=f"Client init failed: {exc}",
            )

    async def generate_json(
        self,
        system_instruction: str,
        prompt: str,
        response_schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 8192,
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """Generate a JSON object. Raises GeminiError on any failure."""
        if not self.configured or self._client is None:
            raise GeminiError(f"Gemini is not configured: {self._status.detail}")

        config: Dict[str, Any] = {
            "system_instruction": system_instruction,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "response_mime_type": "application/json",
        }
        if response_schema:
            config["response_schema"] = response_schema

        def _call() -> Any:
            return self._client.models.generate_content(  # type: ignore[union-attr]
                model=self.model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(**config),
            )

        try:
            response = await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise GeminiError(f"Gemini call timed out after {timeout}s") from exc
        except Exception as exc:
            # If the schema was rejected, retry once without it — JSON mime type
            # plus the schema described in the system instruction is usually enough.
            if response_schema:
                logger.warning(
                    "gemini.schema_call_failed: %s; retrying without response_schema", exc
                )
                config.pop("response_schema", None)
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(_call), timeout=timeout
                    )
                except Exception as retry_exc:
                    raise GeminiError(f"Gemini call failed: {retry_exc}") from retry_exc
            else:
                raise GeminiError(f"Gemini call failed: {exc}") from exc

        text = self._extract_text(response)
        if not text:
            raise GeminiError("Gemini returned an empty response")

        from backend.agent.prompts import extract_json

        try:
            return extract_json(text)
        except ValueError as exc:
            raise GeminiError(f"Gemini returned unparseable JSON: {exc}") from exc

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Pull text out of a GenerateContentResponse across SDK shapes."""
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text

        try:
            candidates = getattr(response, "candidates", None) or []
            chunks = []
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                for part in getattr(content, "parts", None) or []:
                    part_text = getattr(part, "text", None)
                    if isinstance(part_text, str) and part_text.strip():
                        chunks.append(part_text)
            if chunks:
                return "\n".join(chunks)
        except Exception:  # pragma: no cover - defensive
            pass

        return ""
