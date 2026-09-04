from typing import List, Dict, Any
from backend.models.report import StudioOpsReport, Evidence, ComparableTitle
from backend.models.brief import ProjectBrief


def synthesize_report(brief: ProjectBrief, evidence_groups: List[Dict[str, Any]]) -> StudioOpsReport:
    """Create a conservative, evidence-backed StudioOpsReport from collected evidence.

    This is a Phase-1 synthesizer stub. It must not fabricate facts. It
    extracts cited titles and sources from the evidence and produces a
    short executive summary plus neutral recommendations.
    """
    # Flatten evidence and collect unique sources
    flat: List[Dict[str, Any]] = []
    for group in evidence_groups:
        items = group.get("results") or []
        for it in items:
            flat.append(it)

    # Build Evidence list for report
    sources = []
    seen_urls = set()
    for it in flat:
        url = it.get("url") or ""
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        sources.append(Evidence(
            title=it.get("title") or (it.get("raw", {}).get("headline") if it.get("raw") else ""),
            url=url,
            source=it.get("source") or None,
            snippet=it.get("snippet") or None,
            relevance=it.get("relevance") or 0.0,
        ))

    # Extract comparable titles heuristically from evidence titles
    comparables = []
    for s in sources[:6]:
        comparables.append(ComparableTitle(title=s.title or "Unknown", source=s.source))

    # Executive summary: factual and conservative
    exec_summary = f"Research for '{brief.title}' collected {len(sources)} unique sources. Findings are grounded in the cited evidence."

    next_steps = [
        "Review the top cited sources listed in 'sources' for deeper context",
        "Validate audience demand using platform-specific metrics where available",
        "Investigate identified production partners and distribution platforms",
    ]

    report = StudioOpsReport(
        executive_summary=exec_summary,
        key_opportunities=[],
        comparable_titles=comparables,
        market_signals=[],
        production_intelligence=[],
        risks=[],
        next_steps=next_steps,
        sources=sources,
    )

    return report
