"""System instructions and prompt builders for the StudioOps agent.

The anti-fabrication rules in `SYNTHESIS_SYSTEM_INSTRUCTION` are a product
requirement, not a stylistic preference: the report is decision-support for a
real production budget, so an invented statistic or citation is worse than an
acknowledged gap.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from backend.models.brief import ProjectBrief
from backend.models.research import RESEARCH_CATEGORIES

PLANNER_SYSTEM_INSTRUCTION = """\
You are the research planner inside StudioOps, a production-intelligence agent \
for film and television teams.

Given a production brief, decide what must be researched on the live web before \
a producer could make a green-light decision. Output a focused research plan.

Rules:
- Produce between 4 and 8 tasks. Fewer, sharper tasks beat many vague ones.
- Every task must be derived from THIS brief. Never emit generic business or \
market-research queries; this is a film/TV industry tool.
- Each query must be a natural search phrase that would surface entertainment \
industry sources (trade press, streaming data, film commissions, festival and \
production coverage). Include the genre, territory, format, and named \
comparables from the brief where they sharpen the query.
- Do not emit two tasks that would return the same sources.
- If the brief includes explicit research questions, cover each of them.
- Cover a spread of categories rather than clustering on one.
- Prefer concrete phrasing ("Nollywood crime thriller box office 2025") over \
abstract phrasing ("film market analysis").

Categories: %s

Return ONLY JSON matching:
{
  "reasoning": "one or two sentences on what this project needs researched and why",
  "tasks": [
    {
      "category": "one of the categories above",
      "question": "the decision-relevant question this answers",
      "query": "the web search phrase",
      "priority": 1
    }
  ]
}
priority: 1 = most important.
""" % ", ".join(RESEARCH_CATEGORIES)


SYNTHESIS_SYSTEM_INSTRUCTION = """\
You are the analyst inside StudioOps, a production-intelligence agent for film \
and television teams. You turn retrieved web evidence into a Studio Brief that a \
producer, financier, or commissioner will actually act on.

You will receive a production brief and a numbered list of SOURCES. Each source \
has an id (S1, S2, ...), title, publisher, date, and the retrieved text.

Absolute rules:
1. The SOURCES are your only factual basis. If it is not in the sources, it is \
not a fact you may assert.
2. Cite with source ids. Every comparable title, market signal, audience \
insight, competitive observation, opportunity, and risk must list the \
`evidence_ids` it came from.
3. NEVER invent: statistics, box office or viewership numbers, people, \
companies, titles, quotes, dates, URLs, or citations. Do not cite a source id \
that was not given to you.
4. Only populate `metric` when the figure appears verbatim in a source. Do not \
estimate, extrapolate, or convert currencies.
5. Distinguish evidence from inference. When you reason beyond what a source \
states, mark it in the text with "Inference:" and still cite what the inference \
rests on.
6. If the evidence does not support a section, return that section empty and \
add an entry to `evidence_gaps` naming what is missing. An honest gap is more \
valuable than a padded section.
7. Surface conflicts. If sources disagree, say so and cite both.
8. Prefer recent and industry-specific sources. Treat SEO listicles, directory \
pages, and press-release aggregators as weak evidence; do not build a central \
claim on them alone.
9. Write for a professional reader: specific, plain, and free of marketing \
language. No hedging filler, no restating the brief back.
10. Recommendations must be actions this team can take next, each tied to \
something the research actually surfaced.

Return ONLY JSON matching this schema:
{
  "executive_summary": "3-5 sentences: what the research establishes, and what it means for this project",
  "key_opportunities": ["short phrase", ...],
  "comparable_titles": [{"title","year","genre","market","insight","evidence_ids":["S1"]}],
  "market_signals": [{"signal","detail","metric","trend","evidence_ids":["S2"]}],
  "audience_insights": [{"insight","detail","evidence_ids":["S3"]}],
  "competitive_landscape": [{"observation","detail","gap_or_opportunity","evidence_ids":["S4"]}],
  "production_opportunities": [{"title","category","detail","evidence_ids":["S5"]}],
  "risks": [{"title","severity","explanation","recommended_action","evidence_ids":["S6"]}],
  "next_steps": [{"step","rationale"}],
  "evidence_gaps": ["what the research could not establish", ...]
}
trend must be one of: up, down, flat, or null.
severity must be one of: low, medium, high.
category for opportunities: partner, location, distribution, funding, talent.
"""


def build_planner_prompt(brief: ProjectBrief) -> str:
    """Render the production brief into the planner's user prompt."""
    lines = [
        "PRODUCTION BRIEF",
        f"Title: {brief.title}",
    ]
    optional = [
        ("Format", brief.format),
        ("Genre", brief.genre),
        ("Target audience", brief.target_audience),
        ("Geography / territory", brief.geography),
        ("Budget tier", brief.budget_tier),
        ("Production stage", brief.production_stage),
    ]
    lines.extend(f"{label}: {value}" for label, value in optional if value)
    lines.append(f"Description: {brief.description}")

    if brief.research_questions:
        lines.append("")
        lines.append("The producer explicitly wants these answered:")
        lines.extend(f"- {q}" for q in brief.research_questions if q and q.strip())

    lines.append("")
    lines.append("Produce the research plan as JSON.")
    return "\n".join(lines)


def build_synthesis_prompt(brief: ProjectBrief, sources: List[Dict[str, Any]]) -> str:
    """Render brief + retrieved sources into the synthesizer's user prompt."""
    header = [
        "PRODUCTION BRIEF",
        f"Title: {brief.title}",
    ]
    optional = [
        ("Format", brief.format),
        ("Genre", brief.genre),
        ("Target audience", brief.target_audience),
        ("Geography / territory", brief.geography),
        ("Budget tier", brief.budget_tier),
        ("Production stage", brief.production_stage),
    ]
    header.extend(f"{label}: {value}" for label, value in optional if value)
    header.append(f"Description: {brief.description}")

    if brief.research_questions:
        header.append("")
        header.append("Producer's questions:")
        header.extend(f"- {q}" for q in brief.research_questions if q and q.strip())

    blocks = [
        "\n".join(header),
        "",
        f"SOURCES ({len(sources)} retrieved via live web search)",
        "",
    ]

    for src in sources:
        meta = " | ".join(
            part
            for part in (
                src.get("publisher") or "",
                src.get("published_date") or "",
                ", ".join(src.get("categories") or []),
            )
            if part
        )
        blocks.append(f"[{src['id']}] {src.get('title') or src['url']}")
        blocks.append(f"URL: {src['url']}")
        if meta:
            blocks.append(f"Meta: {meta}")
        content = (src.get("content") or "").strip()
        blocks.append(f"Content: {content if content else '(no text retrieved)'}")
        blocks.append("")

    blocks.append(
        "Produce the Studio Brief as JSON. Cite only the source ids listed above."
    )
    return "\n".join(blocks)


def planner_response_schema() -> Dict[str, Any]:
    """JSON schema constraining the planner's structured output."""
    return {
        "type": "object",
        "properties": {
            "reasoning": {"type": "string"},
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": list(RESEARCH_CATEGORIES)},
                        "question": {"type": "string"},
                        "query": {"type": "string"},
                        "priority": {"type": "integer"},
                    },
                    "required": ["category", "question", "query"],
                },
            },
        },
        "required": ["reasoning", "tasks"],
    }


def _cited_array(properties: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
    props = dict(properties)
    props["evidence_ids"] = {"type": "array", "items": {"type": "string"}}
    return {
        "type": "array",
        "items": {"type": "object", "properties": props, "required": required},
    }


def synthesis_response_schema() -> Dict[str, Any]:
    """JSON schema constraining the synthesizer's structured output."""
    string = {"type": "string"}
    nullable_string = {"type": "string", "nullable": True}
    return {
        "type": "object",
        "properties": {
            "executive_summary": string,
            "key_opportunities": {"type": "array", "items": string},
            "comparable_titles": _cited_array(
                {
                    "title": string,
                    "year": nullable_string,
                    "genre": nullable_string,
                    "market": nullable_string,
                    "insight": string,
                },
                ["title", "insight"],
            ),
            "market_signals": _cited_array(
                {
                    "signal": string,
                    "detail": string,
                    "metric": nullable_string,
                    "trend": {
                        "type": "string",
                        "enum": ["up", "down", "flat"],
                        "nullable": True,
                    },
                },
                ["signal", "detail"],
            ),
            "audience_insights": _cited_array(
                {"insight": string, "detail": string}, ["insight", "detail"]
            ),
            "competitive_landscape": _cited_array(
                {
                    "observation": string,
                    "detail": string,
                    "gap_or_opportunity": nullable_string,
                },
                ["observation", "detail"],
            ),
            "production_opportunities": _cited_array(
                {
                    "title": string,
                    "category": {
                        "type": "string",
                        "enum": ["partner", "location", "distribution", "funding", "talent"],
                        "nullable": True,
                    },
                    "detail": string,
                },
                ["title", "detail"],
            ),
            "risks": _cited_array(
                {
                    "title": string,
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "explanation": string,
                    "recommended_action": string,
                },
                ["title", "severity", "explanation"],
            ),
            "next_steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"step": string, "rationale": string},
                    "required": ["step"],
                },
            },
            "evidence_gaps": {"type": "array", "items": string},
        },
        "required": ["executive_summary", "next_steps"],
    }


def extract_json(text: str) -> Dict[str, Any]:
    """Parse a JSON object from model output, tolerating fences and prose.

    Raises ValueError if no JSON object can be recovered.
    """
    if not text:
        raise ValueError("empty model response")

    cleaned = text.strip()

    # Strip ```json fences.
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("no JSON object found in model response")
        parsed = json.loads(cleaned[start : end + 1])

    if not isinstance(parsed, dict):
        raise ValueError(f"expected a JSON object, got {type(parsed).__name__}")
    return parsed
