from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


class EvidenceProcessor:
    """Normalizes, deduplicates, and filters retrieved evidence."""

    def _canonical_url(self, raw_url: str) -> str:
        if not raw_url:
            return ""
        parsed = urlsplit(raw_url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        url = urlunsplit((scheme, netloc, path, "", ""))
        return url.rstrip("/") if url != "http://" else url

    def process(self, results: list[dict]) -> list[dict]:
        by_url: dict[str, dict] = {}

        for item in results:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            canonical = self._canonical_url(url)
            if not canonical:
                continue

            title = str(item.get("title") or "Untitled source").strip()
            snippet = str(item.get("snippet") or item.get("description") or "").strip()
            source_type = item.get("source_type") or "web"
            relevance = float(item.get("relevance") or 0.0)
            entry = {
                "title": title,
                "url": canonical,
                "snippet": snippet,
                "source_type": source_type,
                "relevance": relevance,
                "category": item.get("category"),
                "question": item.get("question"),
            }

            previous = by_url.get(canonical)
            if previous is None or relevance > float(previous.get("relevance") or 0.0):
                by_url[canonical] = entry

        normalized = list(by_url.values())
        normalized.sort(key=lambda v: float(v.get("relevance") or 0.0), reverse=True)
        return normalized
