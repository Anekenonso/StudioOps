"""Report persistence: full JSON plus a readable Markdown Studio Brief."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REPORT_DIR = os.path.join(os.getcwd(), "outputs", "reports")

SEVERITY_LABEL = {"high": "High", "medium": "Medium", "low": "Low"}

SECTION_TITLES = {
    "comparable_titles": "Comparable Projects",
    "market_signals": "Market Landscape",
    "audience_insights": "Audience Intelligence",
    "competitive_landscape": "Competitive Landscape",
    "production_opportunities": "Production Opportunities",
    "risks": "Risks & Considerations",
}


def ensure_dir() -> None:
    os.makedirs(REPORT_DIR, exist_ok=True)


def _slug(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "report").lower()).strip("-")
    return (slug or "report")[:limit]


def _basename(payload: Dict[str, Any]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    title = _slug((payload.get("project") or {}).get("title", "report"))
    run_id = payload.get("run_id") or ""
    suffix = f"-{run_id}" if run_id else ""
    return f"{title}-{ts}{suffix}"


def save_report(payload: Dict[str, Any]) -> Dict[str, str]:
    """Write JSON + Markdown for a run. Returns filenames (not paths)."""
    ensure_dir()
    base = _basename(payload)

    json_name = f"{base}.json"
    with open(os.path.join(REPORT_DIR, json_name), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    md_name = f"{base}.md"
    with open(os.path.join(REPORT_DIR, md_name), "w", encoding="utf-8") as fh:
        fh.write(render_markdown(payload))

    logger.info("report.saved json=%s md=%s", json_name, md_name)
    return {"json": json_name, "md": md_name}


def _cite(evidence_ids: Optional[List[str]], index: Dict[str, Dict[str, Any]]) -> str:
    """Render citations as markdown links back to the Sources section."""
    if not evidence_ids:
        return ""
    parts = []
    for evidence_id in evidence_ids:
        source = index.get(evidence_id)
        if source and source.get("url"):
            parts.append(f"[{evidence_id}]({source['url']})")
        else:
            parts.append(evidence_id)
    return " — Sources: " + ", ".join(parts)


def render_markdown(payload: Dict[str, Any]) -> str:
    """Render the full Studio Brief as Markdown."""
    project = payload.get("project") or {}
    report = payload.get("report") or {}
    meta = payload.get("research_metadata") or {}
    sources = report.get("sources") or []
    index = {s.get("id"): s for s in sources if s.get("id")}

    out: List[str] = []
    add = out.append

    title = project.get("title") or "Studio Brief"
    add(f"# Studio Brief — {title}")
    add("")

    descriptors = [
        project.get("format"),
        project.get("genre"),
        project.get("geography"),
        project.get("target_audience"),
    ]
    line = " · ".join(d.upper() for d in descriptors if d)
    if line:
        add(f"**{line}**")
        add("")

    researched = project.get("researched_at") or ""
    if researched:
        add(f"Researched {researched[:10]} · StudioOps (Gemini + Parallel)")
        add("")

    generated_by = report.get("generated_by")
    if generated_by == "fallback":
        add(
            "> **Note:** Gemini synthesis did not run for this report. The content "
            "below is retrieved web evidence without model analysis."
        )
        add("")

    # Executive summary
    summary = report.get("executive_summary")
    if summary:
        add("## Executive Summary")
        add("")
        add(summary)
        add("")

    # Key opportunities
    opportunities = report.get("key_opportunities") or []
    if opportunities:
        add("## Key Opportunities")
        add("")
        for item in opportunities:
            add(f"- {item}")
        add("")

    notes = report.get("section_notes") or {}

    def section_note(key: str) -> None:
        note = notes.get(key) or {}
        if note.get("insufficient_evidence"):
            add(f"_{note.get('note') or 'Insufficient evidence for this section.'}_")
            add("")

    # Market signals
    add(f"## {SECTION_TITLES['market_signals']}")
    add("")
    signals = report.get("market_signals") or []
    if signals:
        for signal in signals:
            heading = signal.get("signal") or ""
            metric = signal.get("metric")
            trend = signal.get("trend")
            bits = [b for b in (metric, f"trend: {trend}" if trend else None) if b]
            meta_str = f" ({', '.join(bits)})" if bits else ""
            add(f"### {heading}{meta_str}")
            if signal.get("detail"):
                add("")
                add(signal["detail"])
            citation = _cite(signal.get("evidence_ids"), index)
            if citation:
                add("")
                add(citation.lstrip(" —"))
            add("")
    else:
        section_note("market_signals")

    # Comparables
    add(f"## {SECTION_TITLES['comparable_titles']}")
    add("")
    comparables = report.get("comparable_titles") or []
    if comparables:
        for item in comparables:
            descriptor = " · ".join(
                str(v) for v in (item.get("year"), item.get("genre"), item.get("market")) if v
            )
            add(f"### {item.get('title')}")
            if descriptor:
                add(f"_{descriptor}_")
            if item.get("insight"):
                add("")
                add(item["insight"])
            citation = _cite(item.get("evidence_ids"), index)
            if citation:
                add("")
                add(citation.lstrip(" —"))
            add("")
    else:
        section_note("comparable_titles")

    # Audience
    audience = report.get("audience_insights") or []
    add(f"## {SECTION_TITLES['audience_insights']}")
    add("")
    if audience:
        for item in audience:
            add(f"- **{item.get('insight')}** {item.get('detail') or ''}".rstrip())
            citation = _cite(item.get("evidence_ids"), index)
            if citation:
                add(f"  {citation.lstrip(' —')}")
        add("")
    else:
        section_note("audience_insights")

    # Competition
    competitive = report.get("competitive_landscape") or []
    add(f"## {SECTION_TITLES['competitive_landscape']}")
    add("")
    if competitive:
        for item in competitive:
            add(f"### {item.get('observation')}")
            if item.get("detail"):
                add("")
                add(item["detail"])
            if item.get("gap_or_opportunity"):
                add("")
                add(f"**Gap / opportunity:** {item['gap_or_opportunity']}")
            citation = _cite(item.get("evidence_ids"), index)
            if citation:
                add("")
                add(citation.lstrip(" —"))
            add("")
    else:
        section_note("competitive_landscape")

    # Production opportunities
    production = report.get("production_opportunities") or []
    add(f"## {SECTION_TITLES['production_opportunities']}")
    add("")
    if production:
        for item in production:
            label = item.get("category")
            add(f"### {item.get('title')}" + (f" _({label})_" if label else ""))
            if item.get("detail"):
                add("")
                add(item["detail"])
            citation = _cite(item.get("evidence_ids"), index)
            if citation:
                add("")
                add(citation.lstrip(" —"))
            add("")
    else:
        section_note("production_opportunities")

    # Risks
    risks = report.get("risks") or []
    add(f"## {SECTION_TITLES['risks']}")
    add("")
    if risks:
        for risk in risks:
            severity = SEVERITY_LABEL.get((risk.get("severity") or "").lower(), "Medium")
            add(f"### {risk.get('title')} — {severity} severity")
            if risk.get("explanation"):
                add("")
                add(risk["explanation"])
            if risk.get("recommended_action"):
                add("")
                add(f"**Recommended action:** {risk['recommended_action']}")
            citation = _cite(risk.get("evidence_ids"), index)
            if citation:
                add("")
                add(citation.lstrip(" —"))
            add("")
    else:
        section_note("risks")

    # Next steps
    next_steps = report.get("next_steps") or []
    if next_steps:
        add("## Recommended Next Steps")
        add("")
        for i, step in enumerate(next_steps, start=1):
            text = step.get("step") if isinstance(step, dict) else str(step)
            add(f"{i:02d}. **{text}**")
            rationale = step.get("rationale") if isinstance(step, dict) else ""
            if rationale:
                add(f"    {rationale}")
        add("")

    # Evidence gaps
    gaps = report.get("evidence_gaps") or []
    if gaps:
        add("## Evidence Gaps")
        add("")
        for gap in gaps:
            add(f"- {gap}")
        add("")

    # Sources
    if sources:
        add(f"## Sources ({len(sources)})")
        add("")
        for source in sources:
            bits = [source.get("publisher"), source.get("published_date")]
            descriptor = " · ".join(str(b) for b in bits if b)
            heading = f"**{source.get('id')}** — [{source.get('title') or source.get('url')}]({source.get('url')})"
            add(heading + (f"  \n_{descriptor}_" if descriptor else ""))
            snippet = (source.get("snippet") or "").strip()
            if snippet:
                trimmed = snippet[:280] + ("…" if len(snippet) > 280 else "")
                add(f"  \n{trimmed}")
            add("")

    # Research trail
    plan = payload.get("plan") or {}
    tasks = plan.get("tasks") or []
    if tasks:
        add("## Research Trail")
        add("")
        add(f"_Plan generated by: {plan.get('generated_by') or 'unknown'}_")
        if plan.get("reasoning"):
            add("")
            add(plan["reasoning"])
        add("")
        add("| Category | Query | Results | Status |")
        add("| --- | --- | --- | --- |")
        for task in tasks:
            status = "failed" if task.get("error") else "ok"
            query = str(task.get("query") or "").replace("|", "\\|")
            add(
                f"| {task.get('category')} | {query} | "
                f"{task.get('result_count', 0)} | {status} |"
            )
        add("")

    if meta:
        add("---")
        add("")
        add(
            f"Queries run: {meta.get('queries_run', 0)} · "
            f"Sources reviewed: {meta.get('sources_reviewed', 0)} · "
            f"Unique sources: {meta.get('unique_sources', 0)} · "
            f"Total time: {meta.get('total_duration_ms', 0)} ms"
        )
        add("")
        warnings = meta.get("warnings") or []
        if warnings:
            add("**Warnings**")
            add("")
            for warning in warnings:
                add(f"- {warning}")
            add("")

    add("_Generated by StudioOps — production intelligence powered by Gemini + Parallel._")
    return "\n".join(out) + "\n"


# --- Backwards-compatible helpers ------------------------------------------


def save_report_json(payload: Dict[str, Any]) -> str:
    ensure_dir()
    name = f"{_basename(payload)}.json"
    path = os.path.join(REPORT_DIR, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return path


def save_report_markdown(payload: Dict[str, Any]) -> str:
    ensure_dir()
    name = f"{_basename(payload)}.md"
    path = os.path.join(REPORT_DIR, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(payload))
    return path
