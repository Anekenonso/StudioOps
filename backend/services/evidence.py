from __future__ import annotations

from urllib.parse import urlsplit


class EvidenceProcessor:
    """Normalizes, deduplicates, and filters retrieved evidence."""

    def process(self, results: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        seen: set[str] = set()

        for item in results:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            parsed = urlsplit(url)
            canonical = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path or '/'}"
            if canonical in seen:
                continue
            seen.add(canonical)

            title = str(item.get("title") or "Untitled source").strip()
            snippet = str(item.get("snippet") or item.get("description") or "").strip()
            source_type = item.get("source_type") or "web"
            relevance = float(item.get("relevance") or 0.0)

            normalized.append(
                {
                    "title": title,
                    "url": canonical,
                    "snippet": snippet,
                    "source_type": source_type,
                    "relevance": relevance,
                    "category": item.get("category"),
                    "question": item.get("question"),
                }
            )

        normalized.sort(key=lambda v: float(v.get("relevance") or 0.0), reverse=True)
        return normalized
