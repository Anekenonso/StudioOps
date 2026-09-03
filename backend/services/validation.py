from __future__ import annotations

from backend.models.report import StudioOpsReport


def validate_report(report: StudioOpsReport) -> StudioOpsReport:
    cleaned = report.model_copy(deep=True)

    if not cleaned.executive_summary:
        cleaned.executive_summary = "Evidence is insufficient to write a confident executive summary."

    cleaned.key_opportunities = cleaned.key_opportunities or []
    cleaned.comparable_titles = cleaned.comparable_titles or []
    cleaned.market_signals = cleaned.market_signals or []
    cleaned.production_intelligence = cleaned.production_intelligence or []
    cleaned.risks = cleaned.risks or []
    cleaned.next_steps = cleaned.next_steps or []
    cleaned.sources = cleaned.sources or []

    for risk in cleaned.risks:
        risk.evidence_urls = risk.evidence_urls or []

    return cleaned
