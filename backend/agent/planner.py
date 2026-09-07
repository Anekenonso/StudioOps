"""Research planner.

Primary path: Gemini reads the brief and decides what to investigate.
Fallback path: a deterministic, film-aware plan builder used when Gemini is
unconfigured or fails. The fallback is explicitly labelled in the plan
(`generated_by="fallback"`) so the UI and report never present templated
queries as model reasoning.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from backend.agent.prompts import (
    PLANNER_SYSTEM_INSTRUCTION,
    build_planner_prompt,
    planner_response_schema,
)
from backend.integrations.gemini_client import GeminiClient, GeminiError
from backend.models.brief import ProjectBrief
from backend.models.research import RESEARCH_CATEGORIES, ResearchPlan, SearchTask

logger = logging.getLogger(__name__)

MIN_TASKS = 4
MAX_TASKS = 8


async def create_research_plan(
    brief: ProjectBrief, gemini: Optional[GeminiClient] = None
) -> ResearchPlan:
    """Build a research plan for `brief`, preferring Gemini."""
    client = gemini or GeminiClient()

    if client.configured:
        try:
            raw = await client.generate_json(
                system_instruction=PLANNER_SYSTEM_INSTRUCTION,
                prompt=build_planner_prompt(brief),
                response_schema=planner_response_schema(),
                temperature=0.4,
                max_output_tokens=2048,
            )
            plan = _plan_from_model_output(raw)
            if len(plan.tasks) >= 2:
                logger.info("planner.gemini tasks=%d", len(plan.tasks))
                return plan
            logger.warning(
                "planner.gemini_too_few_tasks count=%d; using fallback", len(plan.tasks)
            )
        except GeminiError as exc:
            logger.warning("planner.gemini_failed: %s; using fallback", exc)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("planner.gemini_unexpected_error: %s; using fallback", exc)

    return build_fallback_plan(brief)


def _plan_from_model_output(raw: Dict[str, Any]) -> ResearchPlan:
    """Validate and clean Gemini's plan, dropping malformed or duplicate tasks."""
    tasks: List[SearchTask] = []
    seen_queries: set[str] = set()

    for index, item in enumerate(raw.get("tasks") or [], start=1):
        if not isinstance(item, dict):
            continue

        query = str(item.get("query") or "").strip()
        if not query:
            continue

        dedup_key = _normalize_query(query)
        if dedup_key in seen_queries:
            continue
        seen_queries.add(dedup_key)

        category = str(item.get("category") or "other").strip().lower()
        if category not in RESEARCH_CATEGORIES:
            category = "other"

        try:
            priority = int(item.get("priority") or 3)
        except (TypeError, ValueError):
            priority = 3

        tasks.append(
            SearchTask(
                id=f"t{index}",
                category=category,
                question=str(item.get("question") or query).strip(),
                query=query,
                priority=max(1, min(priority, 5)),
            )
        )

        if len(tasks) >= MAX_TASKS:
            break

    tasks.sort(key=lambda t: t.priority)
    # Reassign ids so they reflect execution order.
    for index, task in enumerate(tasks, start=1):
        task.id = f"t{index}"

    return ResearchPlan(
        reasoning=str(raw.get("reasoning") or "").strip(),
        tasks=tasks,
        generated_by="gemini",
    )


def _normalize_query(query: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", query.lower()).strip()


def build_fallback_plan(brief: ProjectBrief) -> ResearchPlan:
    """Deterministic film/TV research plan derived from the brief.

    Used when Gemini is unavailable. Every query is anchored to entertainment
    industry vocabulary so the searches stay on-domain even when the brief
    omits genre or territory.
    """
    genre = (brief.genre or "").strip()
    territory = (brief.geography or "").strip()
    fmt = (brief.format or "").strip()
    audience = (brief.target_audience or "").strip()

    keywords = _extract_keywords(brief)

    # Descriptors that keep queries inside the film/TV domain.
    work = _format_noun(fmt)
    subject = " ".join(part for part in (genre, work) if part) or work
    place = territory or "international"
    topic = keywords or genre or brief.title

    tasks: List[Dict[str, str]] = [
        {
            "category": "comparables",
            "question": f"Which recent titles are comparable to {brief.title}?",
            "query": f"recent {subject} released in {place} comparable titles",
        },
        {
            "category": "market",
            "question": f"What is the state of the {place} {work} market?",
            "query": f"{place} film and television industry market size box office {work} 2025 2026",
        },
        {
            "category": "audience",
            "question": "What audience demand signals exist for this kind of project?",
            "query": (
                f"{audience or 'streaming'} audience demand for {genre or 'drama'} "
                f"{work} in {place} viewership data"
            ),
        },
        {
            "category": "competition",
            "question": "What competing content is already serving this audience?",
            "query": f"streaming platforms commissioning {subject} in {place} competition",
        },
        {
            "category": "production",
            "question": "Which production companies and locations are relevant?",
            "query": f"{place} production companies producing {genre or 'scripted'} {work} film commission locations",
        },
        {
            "category": "distribution",
            "question": "What distribution and financing routes are available?",
            "query": f"{place} {work} distribution deals streaming acquisition financing funds",
        },
        {
            "category": "developments",
            "question": "What recent industry developments affect this project?",
            "query": f"{place} film industry news 2026 {genre or 'production'} developments trade press",
        },
    ]

    if topic and topic.lower() not in (genre.lower(), brief.title.lower()):
        tasks.append(
            {
                "category": "other",
                "question": f"What does the research say about {topic}?",
                "query": f"{topic} {genre or ''} {work} industry coverage".replace("  ", " ").strip(),
            }
        )

    # Cover explicit producer questions, which take priority over generic coverage.
    question_tasks: List[Dict[str, str]] = []
    for question in (brief.research_questions or [])[:3]:
        question = (question or "").strip()
        if not question:
            continue
        question_tasks.append(
            {
                "category": "other",
                "question": question,
                "query": _question_to_query(question, genre, place, work),
            }
        )

    combined = question_tasks + tasks
    search_tasks: List[SearchTask] = []
    seen: set[str] = set()

    for item in combined:
        query = re.sub(r"\s+", " ", item["query"]).strip()
        key = _normalize_query(query)
        if not query or key in seen:
            continue
        seen.add(key)
        search_tasks.append(
            SearchTask(
                id=f"t{len(search_tasks) + 1}",
                category=item["category"],
                question=item["question"],
                query=query,
                priority=len(search_tasks) + 1,
            )
        )
        if len(search_tasks) >= MAX_TASKS:
            break

    reasoning = (
        f"Deterministic plan for a {genre or 'scripted'} {work} in {place}: "
        "comparables, market and audience demand, competition, production and "
        "distribution routes, and recent industry developments."
    )

    return ResearchPlan(reasoning=reasoning, tasks=search_tasks, generated_by="fallback")


def _format_noun(fmt: str) -> str:
    """Map a user-supplied format to search-friendly industry vocabulary."""
    normalized = fmt.lower()
    if not normalized:
        return "film or series"
    if "series" in normalized or "tv" in normalized or "television" in normalized:
        return "series"
    if "doc" in normalized:
        return "documentary"
    if "short" in normalized:
        return "short film"
    if "film" in normalized or "feature" in normalized or "movie" in normalized:
        return "film"
    return fmt


_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "for", "with", "about", "into", "from",
    "this", "that", "these", "those", "we", "our", "us", "it", "its", "is", "are",
    "was", "were", "be", "been", "being", "of", "in", "on", "at", "to", "as", "by",
    "developing", "develop", "project", "research", "want", "understand", "current",
    "set", "designed", "aimed", "story", "film", "movie", "series", "show", "new",
    "contemporary", "modern", "local", "international", "audience", "market",
}


def _extract_keywords(brief: ProjectBrief, limit: int = 3) -> str:
    """Pull distinctive terms from the description to sharpen fallback queries.

    Prefers capitalized multi-word phrases (place names, named entities), then
    falls back to frequent content words.
    """
    text = f"{brief.description or ''}"
    if not text.strip():
        return ""

    proper = re.findall(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*)\b", text)
    picks: List[str] = []
    known = {
        (brief.title or "").lower(),
        (brief.genre or "").lower(),
        (brief.geography or "").lower(),
    }

    for phrase in proper:
        low = phrase.lower()
        if low in known or low in _STOPWORDS:
            continue
        if any(low in existing.lower() or existing.lower() in low for existing in picks):
            continue
        picks.append(phrase)
        if len(picks) >= limit:
            break

    if picks:
        return " ".join(picks)

    words = [w for w in re.findall(r"[a-zA-Z]{4,}", text.lower()) if w not in _STOPWORDS]
    seen: set[str] = set()
    unique = []
    for word in words:
        if word in seen:
            continue
        seen.add(word)
        unique.append(word)
    return " ".join(unique[:limit])


_QUESTION_LEADS = {
    "what", "which", "who", "whom", "whose", "how", "why", "where", "when",
    "are", "is", "was", "were", "do", "does", "did", "can", "could", "should",
    "would", "will", "there", "any", "the", "a", "an",
}

# Clause tails that read as grammar rather than search terms once the leading
# interrogative is removed ("...and how did they perform?").
_TRAILING_NOISE = re.compile(
    r"\b(?:and\s+)?(?:how|why|whether|if)\s+(?:did|do|does|is|are|was|were|they|it|we|you)\b.*$",
    re.IGNORECASE,
)


def _question_to_query(question: str, genre: str, place: str, work: str) -> str:
    """Turn a producer's question into a domain-anchored search phrase.

    Search engines match noun phrases, not questions, so the interrogative
    framing is stripped and the project's genre/format/territory appended —
    but only the parts not already present, to avoid duplicated terms.
    """
    stripped = question.strip().rstrip("?").strip()
    stripped = _TRAILING_NOISE.sub("", stripped).strip(" ,;–—-")

    words = re.findall(r"[A-Za-z0-9'&/]+", stripped)
    # Drop leading interrogatives/auxiliaries only; keep them mid-phrase where
    # they may carry meaning (e.g. "rights and who owns them").
    while words and words[0].lower() in _QUESTION_LEADS:
        words.pop(0)

    core = " ".join(words[:12]).strip() or stripped
    core_lower = core.lower()

    context = [
        part
        for part in (genre, work, place)
        if part and part.lower() not in core_lower
    ]
    return re.sub(r"\s+", " ", f"{core} {' '.join(context)}").strip()
