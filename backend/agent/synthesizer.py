"""Report synthesis.

Primary path: Gemini reasons over the retrieved evidence and returns a
structured Studio Brief.

Every model-produced claim passes through `_validate_citations`, which drops
citation ids that were not in the evidence corpus. A claim left with no valid
citation is discarded rather than published uncited — this is the enforcement
point for "never fabricate citations".

Fallback path: when Gemini is unconfigured or fails, `build_fallback_report`
returns the retrieved sources grouped by research category with no invented
analysis, and says so plainly in the summary.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Set

from backend.agent.prompts import (
    SYNTHESIS_SYSTEM_INSTRUCTION,
    build_synthesis_prompt,
    synthesis_response_schema,
)
from backend.integrations.gemini_client import GeminiClient, GeminiError
from backend.models.brief import ProjectBrief
from backend.models.report import (
    AudienceInsight,
    ComparableTitle,
    CompetitiveInsight,
    MarketSignal,
    NextStep,
    Opportunity,
    ReportSection,
    Risk,
    StudioOpsReport,
)
from backend.models.research import CATEGORY_LABELS, Evidence, ResearchContext

logger = logging.getLogger(__name__)

# Sources sent to the model. Bounded to control token cost per the spec's
# cost-control section; sources are pre-sorted by relevance.
MAX_PROMPT_SOURCES = 40

_SECTION_KEYS = (
    "comparable_titles",
    "market_signals",
    "audience_insights",
    "competitive_landscape",
    "production_opportunities",
    "risks",
)


async def synthesize_report(
    brief: ProjectBrief,
    context: ResearchContext,
    gemini: Optional[GeminiClient] = None,
) -> StudioOpsReport:
    """Produce a Studio Brief from retrieved evidence."""
    if not context.evidence:
        return build_empty_report(brief, context)

    client = gemini or GeminiClient()

    if client.configured:
        try:
            sources = context.as_prompt_payload()[:MAX_PROMPT_SOURCES]
            raw = await client.generate_json(
                system_instruction=SYNTHESIS_SYSTEM_INSTRUCTION,
                prompt=build_synthesis_prompt(brief, sources),
                response_schema=synthesis_response_schema(),
                temperature=0.25,
                max_output_tokens=8192,
            )
            report = _report_from_model_output(raw, context)
            if report.executive_summary.strip():
                logger.info(
                    "synthesizer.gemini comparables=%d signals=%d risks=%d",
                    len(report.comparable_titles),
                    len(report.market_signals),
                    len(report.risks),
                )
                return report
            logger.warning("synthesizer.gemini_empty_summary; using fallback")
        except GeminiError as exc:
            logger.warning("synthesizer.gemini_failed: %s; using fallback", exc)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("synthesizer.gemini_unexpected_error: %s; using fallback", exc)

    return build_fallback_report(brief, context)


def _report_from_model_output(
    raw: Dict[str, Any], context: ResearchContext
) -> StudioOpsReport:
    """Validate model output into a StudioOpsReport, enforcing real citations."""
    valid_ids: Set[str] = {e.id for e in context.evidence}
    dropped_citations = 0
    dropped_claims = 0

    def cited(item: Dict[str, Any], require: bool = True):
        """Filter an item's evidence_ids to real ids. Returns None to drop."""
        nonlocal dropped_citations, dropped_claims
        ids = item.get("evidence_ids") or []
        if isinstance(ids, str):
            ids = [ids]
        clean = []
        for raw_id in ids:
            candidate = str(raw_id).strip().upper()
            if candidate in valid_ids:
                if candidate not in clean:
                    clean.append(candidate)
            else:
                dropped_citations += 1
        if require and not clean:
            dropped_claims += 1
            return None
        return clean

    def text(item: Dict[str, Any], key: str, default: str = "") -> str:
        value = item.get(key)
        return str(value).strip() if value not in (None, "") else default

    def optional(item: Dict[str, Any], key: str) -> Optional[str]:
        value = item.get(key)
        if value in (None, "", "null", "N/A", "n/a", "unknown"):
            return None
        return str(value).strip()

    def rows(key: str) -> List[Dict[str, Any]]:
        return [r for r in (raw.get(key) or []) if isinstance(r, dict)]

    comparables: List[ComparableTitle] = []
    for row in rows("comparable_titles"):
        ids = cited(row)
        title = text(row, "title")
        if ids is None or not title:
            continue
        comparables.append(
            ComparableTitle(
                title=title,
                year=optional(row, "year"),
                genre=optional(row, "genre"),
                market=optional(row, "market"),
                insight=text(row, "insight"),
                evidence_ids=ids,
            )
        )

    signals: List[MarketSignal] = []
    for row in rows("market_signals"):
        ids = cited(row)
        signal = text(row, "signal")
        if ids is None or not signal:
            continue
        trend = optional(row, "trend")
        if trend not in ("up", "down", "flat", None):
            trend = None
        signals.append(
            MarketSignal(
                signal=signal,
                detail=text(row, "detail"),
                metric=optional(row, "metric"),
                trend=trend,
                evidence_ids=ids,
            )
        )

    audience: List[AudienceInsight] = []
    for row in rows("audience_insights"):
        ids = cited(row)
        insight = text(row, "insight")
        if ids is None or not insight:
            continue
        audience.append(
            AudienceInsight(
                insight=insight, detail=text(row, "detail"), evidence_ids=ids
            )
        )

    competitive: List[CompetitiveInsight] = []
    for row in rows("competitive_landscape"):
        ids = cited(row)
        observation = text(row, "observation")
        if ids is None or not observation:
            continue
        competitive.append(
            CompetitiveInsight(
                observation=observation,
                detail=text(row, "detail"),
                gap_or_opportunity=optional(row, "gap_or_opportunity"),
                evidence_ids=ids,
            )
        )

    opportunities: List[Opportunity] = []
    for row in rows("production_opportunities"):
        ids = cited(row)
        title = text(row, "title")
        if ids is None or not title:
            continue
        category = optional(row, "category")
        if category not in ("partner", "location", "distribution", "funding", "talent", None):
            category = None
        opportunities.append(
            Opportunity(
                title=title,
                category=category,
                detail=text(row, "detail"),
                evidence_ids=ids,
            )
        )

    risks: List[Risk] = []
    for row in rows("risks"):
        # A risk may be a reasoned judgement rather than a sourced claim, so
        # citations are encouraged but not mandatory here.
        ids = cited(row, require=False) or []
        title = text(row, "title")
        if not title:
            continue
        severity = (optional(row, "severity") or "medium").lower()
        if severity not in ("low", "medium", "high"):
            severity = "medium"
        risks.append(
            Risk(
                title=title,
                severity=severity,
                explanation=text(row, "explanation"),
                recommended_action=text(row, "recommended_action"),
                evidence_ids=ids,
            )
        )

    next_steps: List[NextStep] = []
    for row in rows("next_steps"):
        step = text(row, "step")
        if step:
            next_steps.append(NextStep(step=step, rationale=text(row, "rationale")))
    # Tolerate a plain string array for next_steps.
    if not next_steps:
        for row in raw.get("next_steps") or []:
            if isinstance(row, str) and row.strip():
                next_steps.append(NextStep(step=row.strip()))

    opportunities_summary = [
        str(o).strip()
        for o in (raw.get("key_opportunities") or [])
        if isinstance(o, str) and str(o).strip()
    ]
    gaps = [
        str(g).strip()
        for g in (raw.get("evidence_gaps") or [])
        if isinstance(g, str) and str(g).strip()
    ]

    if dropped_citations or dropped_claims:
        logger.warning(
            "synthesizer.citations_rejected invalid_ids=%d claims_dropped=%d",
            dropped_citations,
            dropped_claims,
        )
        context.metadata.warnings.append(
            f"Rejected {dropped_citations} unverifiable citation(s) and dropped "
            f"{dropped_claims} uncited claim(s) during validation."
        )

    report = StudioOpsReport(
        executive_summary=str(raw.get("executive_summary") or "").strip(),
        key_opportunities=opportunities_summary,
        comparable_titles=comparables,
        market_signals=signals,
        audience_insights=audience,
        competitive_landscape=competitive,
        production_opportunities=opportunities,
        risks=risks,
        next_steps=next_steps,
        evidence_gaps=gaps,
        sources=_cited_sources(context, [
            comparables, signals, audience, competitive, opportunities, risks
        ]),
        generated_by="gemini",
    )
    _annotate_empty_sections(report)
    return report


def _cited_sources(
    context: ResearchContext, claim_groups: Sequence[Sequence[Any]]
) -> List[Evidence]:
    """Return retrieved sources, cited ones first, in citation order.

    All retrieved sources are kept — the Sources section documents the full
    research trail — but the ones the report actually leans on lead.
    """
    order: List[str] = []
    for group in claim_groups:
        for claim in group:
            for evidence_id in getattr(claim, "evidence_ids", []) or []:
                if evidence_id not in order:
                    order.append(evidence_id)

    by_id = context.evidence_by_id()
    cited = [by_id[i] for i in order if i in by_id]
    cited_ids = {e.id for e in cited}
    uncited = [e for e in context.evidence if e.id not in cited_ids]
    return cited + uncited


def _annotate_empty_sections(report: StudioOpsReport) -> None:
    """Mark empty sections so the UI shows an honest gap, not a blank panel."""
    for key in _SECTION_KEYS:
        if not getattr(report, key, None):
            report.section_notes[key] = ReportSection(
                insufficient_evidence=True,
                note="The retrieved research did not support findings for this section.",
            )


def build_empty_report(brief: ProjectBrief, context: ResearchContext) -> StudioOpsReport:
    """Report for a run where no usable evidence was retrieved."""
    failed = [t for t in context.task_results if not t.ok]
    if failed:
        summary = (
            f"Research for '{brief.title}' could not be completed: "
            f"{len(failed)} of {len(context.task_results)} web searches failed. "
            "No evidence was retrieved, so no findings are reported."
        )
    else:
        summary = (
            f"Research for '{brief.title}' returned no usable sources. The live "
            "web search completed but retrieved no substantive content, so no "
            "findings are reported."
        )

    report = StudioOpsReport(
        executive_summary=summary,
        evidence_gaps=["No web evidence was retrieved for this brief."],
        next_steps=[
            NextStep(
                step="Re-run the research with a more specific brief",
                rationale="Naming the genre, territory, and format materially improves retrieval.",
            )
        ],
        generated_by="fallback",
    )
    _annotate_empty_sections(report)
    return report


def build_fallback_report(brief: ProjectBrief, context: ResearchContext) -> StudioOpsReport:
    """Evidence-only report used when Gemini synthesis is unavailable.

    Reports what was retrieved and where, and asserts nothing beyond it. No
    analysis is invented, and the summary states that synthesis did not run.
    """
    evidence = context.evidence
    by_category: Dict[str, List[Evidence]] = {}
    for item in evidence:
        for category in item.categories or ["other"]:
            by_category.setdefault(category, []).append(item)

    covered = ", ".join(
        CATEGORY_LABELS.get(c, c).replace("Searching ", "")
        for c in by_category
    )
    publishers = []
    for item in evidence[:8]:
        if item.publisher and item.publisher not in publishers:
            publishers.append(item.publisher)

    summary = (
        f"Live web research for '{brief.title}' retrieved {len(evidence)} unique "
        f"sources across {len(context.task_results)} searches"
        + (f", covering {covered}. " if covered else ". ")
        + "Gemini synthesis did not run for this report, so the sources below are "
        "presented without analysis. Each entry links to the retrieved page."
    )
    if publishers:
        summary += " Leading publishers: " + ", ".join(publishers[:5]) + "."

    signals: List[MarketSignal] = []
    for category in ("market", "audience", "developments", "competition"):
        for item in by_category.get(category, [])[:3]:
            signals.append(
                MarketSignal(
                    signal=item.title,
                    detail=(item.snippet[:400] + "…") if len(item.snippet) > 400 else item.snippet,
                    evidence_ids=[item.id],
                )
            )

    comparables: List[ComparableTitle] = [
        ComparableTitle(
            title=item.title,
            market=brief.geography,
            insight=(item.snippet[:300] + "…") if len(item.snippet) > 300 else item.snippet,
            evidence_ids=[item.id],
        )
        for item in by_category.get("comparables", [])[:6]
    ]

    opportunities: List[Opportunity] = [
        Opportunity(
            title=item.title,
            category="partner" if category == "production" else "distribution",
            detail=(item.snippet[:300] + "…") if len(item.snippet) > 300 else item.snippet,
            evidence_ids=[item.id],
        )
        for category in ("production", "distribution")
        for item in by_category.get(category, [])[:3]
    ]

    failed = [t for t in context.task_results if not t.ok]
    gaps = [
        "Gemini synthesis was unavailable, so this report contains retrieved "
        "evidence without analysis, comparison, or risk assessment."
    ]
    if failed:
        gaps.append(
            f"{len(failed)} of {len(context.task_results)} searches failed: "
            + "; ".join(f"{t.task.category}" for t in failed[:4])
        )

    report = StudioOpsReport(
        executive_summary=summary,
        key_opportunities=[],
        comparable_titles=comparables,
        market_signals=signals,
        production_opportunities=opportunities,
        next_steps=[
            NextStep(
                step="Review the retrieved sources below",
                rationale="They are the primary research output for this run.",
            ),
            NextStep(
                step="Configure Gemini credentials and re-run to generate analysis",
                rationale="Synthesis converts these sources into comparisons, risks, and recommendations.",
            ),
        ],
        evidence_gaps=gaps,
        sources=list(evidence),
        generated_by="fallback",
    )
    _annotate_empty_sections(report)
    return report
