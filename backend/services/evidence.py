"""Evidence processing: normalize, deduplicate, score, and assign citation ids.

Parallel returns overlapping results across queries. This module collapses them
into one deduplicated corpus where each source has a stable id (S1, S2, ...)
that the synthesizer cites and the report resolves back to a URL.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import urlparse

from backend.models.research import Evidence, SearchTask

logger = logging.getLogger(__name__)

# Minimum retrieved text for a source to be worth sending to the synthesizer.
MIN_USEFUL_CHARS = 80

# Domains that return directory/aggregator pages rather than reporting. Kept as
# a relevance penalty rather than a hard filter — occasionally the only source
# on an obscure company is a directory entry.
_LOW_VALUE_DOMAINS = {
    "tracxn.com",
    "prnewswire.com",
    "businesswire.com",
    "prnasia.com",
    "streetinsider.com",
    "globenewswire.com",
    "einpresswire.com",
    "openpr.com",
    "issuewire.com",
}

# Domains that are strong signals for entertainment-industry research.
_INDUSTRY_DOMAINS = {
    "variety.com",
    "deadline.com",
    "hollywoodreporter.com",
    "screendaily.com",
    "thewrap.com",
    "indiewire.com",
    "boxofficemojo.com",
    "the-numbers.com",
    "imdb.com",
    "bfi.org.uk",
    "nollywoodreporter.com",
    "businessday.ng",
    "premiumtimesng.com",
    "guardian.ng",
    "netflix.com",
    "ampereanalysis.com",
    "omdia.com",
    "statista.com",
    "unesco.org",
}

_FILM_TERMS = (
    "film", "movie", "cinema", "series", "season", "episode", "streaming",
    "box office", "nollywood", "hollywood", "bollywood", "producer", "production",
    "director", "screen", "audience", "viewership", "distributor", "distribution",
    "festival", "netflix", "prime video", "showmax", "documentary", "studio",
    "commission", "greenlight", "cast", "genre", "theatrical", "broadcaster",
)


def _domain(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return ""
    return host[4:] if host.startswith("www.") else host


def _registrable(domain: str) -> str:
    """Approximate the registrable domain (handles common two-part TLDs)."""
    parts = domain.split(".")
    if len(parts) <= 2:
        return domain
    if parts[-2] in {"co", "com", "org", "net", "gov", "ac"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def score_relevance(item: Dict[str, Any], text: str) -> float:
    """Heuristic 0..1 relevance score.

    Rewards retrieved text volume, industry-domain provenance, film vocabulary,
    and a publication date; penalizes directory/press-release aggregators. This
    orders sources for the prompt budget — it is not presented as a confidence
    measure.
    """
    score = 0.35
    domain = _registrable(_domain(item.get("url") or ""))
    lowered = text.lower()

    length = len(text)
    if length >= 1200:
        score += 0.2
    elif length >= 400:
        score += 0.12
    elif length >= MIN_USEFUL_CHARS:
        score += 0.05
    else:
        score -= 0.15

    if domain in _INDUSTRY_DOMAINS:
        score += 0.2
    if domain in _LOW_VALUE_DOMAINS:
        score -= 0.25

    term_hits = sum(1 for term in _FILM_TERMS if term in lowered)
    score += min(term_hits, 6) * 0.03

    if item.get("published_date"):
        score += 0.05

    return round(max(0.0, min(score, 1.0)), 3)


def process_evidence(
    task_results: Iterable[Tuple[SearchTask, List[Dict[str, Any]]]],
    max_sources: int = 60,
) -> Tuple[List[Evidence], Dict[str, List[str]]]:
    """Merge per-task Parallel results into a deduplicated evidence corpus.

    Returns `(evidence, task_id -> [evidence_id])`. Sources are ordered by
    relevance and assigned ids S1..Sn in that order, so the highest-value
    sources land first in the synthesis prompt.
    """
    merged: Dict[str, Dict[str, Any]] = {}
    task_urls: Dict[str, List[str]] = {}

    for task, results in task_results:
        urls_for_task: List[str] = []

        for item in results:
            url = (item.get("url") or "").strip()
            if not url:
                continue

            excerpts = [e for e in (item.get("excerpts") or []) if e and e.strip()]
            text = " ".join(excerpts) or (item.get("snippet") or "")

            if len(text.strip()) < MIN_USEFUL_CHARS and not excerpts:
                # No retrieved content: nothing for the synthesizer to reason over.
                continue

            urls_for_task.append(url)
            existing = merged.get(url)

            if existing is None:
                merged[url] = {
                    "title": item.get("title") or "",
                    "url": url,
                    "publisher": item.get("publisher") or _domain(url),
                    "published_date": item.get("published_date"),
                    "excerpts": list(excerpts),
                    "snippet": text,
                    "categories": [task.category],
                    "queries": [task.query],
                }
            else:
                # Same page found by another query: merge coverage, keep new excerpts.
                if task.category not in existing["categories"]:
                    existing["categories"].append(task.category)
                if task.query not in existing["queries"]:
                    existing["queries"].append(task.query)
                for excerpt in excerpts:
                    if excerpt not in existing["excerpts"]:
                        existing["excerpts"].append(excerpt)
                existing["snippet"] = " ".join(existing["excerpts"]) or existing["snippet"]
                if not existing.get("published_date") and item.get("published_date"):
                    existing["published_date"] = item.get("published_date")

        task_urls[task.id] = urls_for_task

    scored = []
    for url, data in merged.items():
        text = " ".join(data["excerpts"]) or data["snippet"]
        relevance = score_relevance(data, text)
        # Sources found by multiple queries are corroborated; nudge them up.
        if len(data["queries"]) > 1:
            relevance = round(min(1.0, relevance + 0.05), 3)
        data["relevance"] = relevance
        scored.append((relevance, url, data))

    scored.sort(key=lambda row: (-row[0], row[1]))
    scored = scored[:max_sources]

    evidence: List[Evidence] = []
    url_to_id: Dict[str, str] = {}

    for index, (_, url, data) in enumerate(scored, start=1):
        evidence_id = f"S{index}"
        url_to_id[url] = evidence_id
        evidence.append(
            Evidence(
                id=evidence_id,
                title=_clean_title(data["title"], url),
                url=url,
                publisher=data.get("publisher") or None,
                published_date=data.get("published_date"),
                snippet=_clean_snippet(data.get("snippet") or ""),
                excerpts=[_clean_snippet(e) for e in data.get("excerpts") or []],
                categories=data.get("categories") or [],
                queries=data.get("queries") or [],
                relevance=data.get("relevance") or 0.0,
            )
        )

    task_evidence_ids = {
        task_id: [url_to_id[u] for u in urls if u in url_to_id]
        for task_id, urls in task_urls.items()
    }

    logger.info(
        "evidence.processed unique=%d dropped_no_text=%d",
        len(evidence),
        max(0, len(merged) - len(evidence)),
    )
    return evidence, task_evidence_ids


def _clean_title(title: str, url: str) -> str:
    title = (title or "").strip()
    if not title or title.lower().startswith(("http://", "https://")):
        return _domain(url) or url
    # Parallel occasionally returns HTML entities inside titles.
    title = _unescape(title)
    return re.sub(r"\s+", " ", title)[:250]


def _clean_snippet(text: str) -> str:
    text = _unescape(text or "")
    text = re.sub(r"<[^>]{1,40}>", "", text)  # strip stray inline tags
    return re.sub(r"[ \t]+", " ", text).strip()


def _unescape(text: str) -> str:
    replacements = {
        "&#x27;": "'",
        "&#39;": "'",
        "&quot;": '"',
        "&amp;": "&",
        "&nbsp;": " ",
        "&lt;": "<",
        "&gt;": ">",
        "&#8217;": "’",
        "&#8212;": "—",
    }
    for needle, replacement in replacements.items():
        text = text.replace(needle, replacement)
    return text
