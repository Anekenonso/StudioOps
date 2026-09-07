"""Report persistence: JSON + Markdown Studio Brief rendering.

The Markdown file is what a producer forwards to a financier, so the citation
links and the "synthesis did not run" banner are load-bearing: a report that
loses its provenance on the way to disk is worse than no report.
"""

from __future__ import annotations

import json
import os

from backend.tools import report_store
from backend.tools.report_store import (
    _basename,
    _slug,
    render_markdown,
    save_report,
)


def source(source_id="S1", **overrides):
    payload = {
        "id": source_id,
        "title": "Nollywood streaming surge",
        "url": f"https://variety.com/{source_id.lower()}",
        "publisher": "variety.com",
        "published_date": "2026-01-02",
        "snippet": "Nigerian scripted commissions rose sharply.",
        "categories": ["market"],
    }
    payload.update(overrides)
    return payload


def payload(**overrides):
    """A complete run payload, matching what the API returns."""
    base = {
        "run_id": "abc123",
        "status": "completed",
        "project": {
            "title": "Lagos After Dark",
            "format": "Series",
            "genre": "Crime Thriller",
            "geography": "Nigeria",
            "target_audience": "Young adults",
            "researched_at": "2026-03-04T10:11:12+00:00",
        },
        "plan": {
            "generated_by": "gemini",
            "reasoning": "The project needs comparables and buyer appetite.",
            "tasks": [
                {
                    "id": "t1",
                    "category": "comparables",
                    "query": "Nollywood crime thriller series streaming",
                    "result_count": 3,
                },
                {
                    "id": "t2",
                    "category": "market",
                    "query": "Nigeria television market size",
                    "result_count": 0,
                    "error": "search timeout",
                },
            ],
        },
        "report": {
            "generated_by": "gemini",
            "executive_summary": "Nigerian scripted drama is drawing global buyers.",
            "key_opportunities": ["Co-production with a regional streamer"],
            "comparable_titles": [
                {
                    "title": "King of Boys",
                    "year": "2018",
                    "genre": "Crime",
                    "market": "Nigeria",
                    "insight": "Proved local crime drama travels.",
                    "evidence_ids": ["S1"],
                }
            ],
            "market_signals": [
                {
                    "signal": "Commission volume rising",
                    "detail": "Streamers doubled local orders.",
                    "metric": "2x year on year",
                    "trend": "up",
                    "evidence_ids": ["S1", "S2"],
                }
            ],
            "audience_insights": [
                {
                    "insight": "Under-35 mobile-first viewing",
                    "detail": "Most streaming happens on phones.",
                    "evidence_ids": ["S2"],
                }
            ],
            "competitive_landscape": [
                {
                    "observation": "Few premium crime series",
                    "detail": "The slate skews to comedy.",
                    "gap_or_opportunity": "Premium crime is underserved.",
                    "evidence_ids": ["S1"],
                }
            ],
            "production_opportunities": [
                {
                    "title": "Lagos State film office",
                    "category": "location",
                    "detail": "Offers permitting support.",
                    "evidence_ids": ["S2"],
                }
            ],
            "risks": [
                {
                    "title": "Currency volatility",
                    "severity": "high",
                    "explanation": "Budgets shift with the naira.",
                    "recommended_action": "Price in USD where possible.",
                    "evidence_ids": ["S1"],
                }
            ],
            "next_steps": [
                {"step": "Approach regional streamers", "rationale": "They are buying."}
            ],
            "evidence_gaps": ["No verified per-episode budget figures."],
            "sources": [source("S1"), source("S2")],
            "section_notes": {},
        },
        "research_metadata": {
            "queries_run": 2,
            "sources_reviewed": 5,
            "unique_sources": 2,
            "total_duration_ms": 4200,
            "warnings": [],
        },
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = {**base[key], **value}
        else:
            base[key] = value
    return base


class TestSlug:
    def test_lowercases_and_hyphenates(self):
        assert _slug("Lagos After Dark!") == "lagos-after-dark"

    def test_collapses_runs_of_punctuation(self):
        assert _slug("A -- B / C") == "a-b-c"

    def test_truncates_to_the_limit(self):
        assert len(_slug("x" * 200)) == 40

    def test_falls_back_when_nothing_survives(self):
        assert _slug("!!!") == "report"

    def test_falls_back_on_empty_input(self):
        assert _slug("") == "report"


class TestBasename:
    def test_carries_title_timestamp_and_run_id(self):
        name = _basename(payload())

        assert name.startswith("lagos-after-dark-")
        assert name.endswith("-abc123")
        assert "T" in name and "Z" in name  # UTC timestamp

    def test_omits_the_run_id_when_absent(self):
        assert not _basename(payload(run_id="")).endswith("-")

    def test_survives_a_payload_with_no_project(self):
        assert _basename({}).startswith("report-")


class TestSaveReport:
    def test_writes_both_formats_and_returns_filenames(self, tmp_path):
        names = save_report(payload())

        assert set(names) == {"json", "md"}
        for name in names.values():
            # Filenames, not paths — the API turns these into /reports/<name> URLs.
            assert os.sep not in name and "/" not in name
            assert os.path.exists(os.path.join(report_store.REPORT_DIR, name))

    def test_the_two_files_share_a_basename(self):
        names = save_report(payload())
        assert names["json"][:-5] == names["md"][:-3]

    def test_json_round_trips_the_payload(self):
        original = payload()
        names = save_report(original)

        with open(os.path.join(report_store.REPORT_DIR, names["json"]), encoding="utf-8") as fh:
            assert json.load(fh) == original

    def test_markdown_matches_the_renderer(self):
        data = payload()
        names = save_report(data)

        with open(os.path.join(report_store.REPORT_DIR, names["md"]), encoding="utf-8") as fh:
            assert fh.read() == render_markdown(data)

    def test_preserves_non_ascii_content(self):
        data = payload(project={"title": "Café Noir"})
        names = save_report(data)

        with open(os.path.join(report_store.REPORT_DIR, names["md"]), encoding="utf-8") as fh:
            assert "Café Noir" in fh.read()

    def test_creates_a_missing_output_directory(self, monkeypatch, tmp_path):
        """First run on a fresh container has no outputs/ directory."""
        target = tmp_path / "nested" / "reports"
        monkeypatch.setattr(report_store, "REPORT_DIR", str(target))

        save_report(payload())
        assert target.is_dir()


class TestMarkdownHeader:
    def test_titles_the_brief(self):
        assert "# Studio Brief — Lagos After Dark" in render_markdown(payload())

    def test_renders_the_descriptor_line(self):
        assert "**SERIES · CRIME THRILLER · NIGERIA · YOUNG ADULTS**" in render_markdown(payload())

    def test_omits_the_descriptor_line_for_a_bare_project(self):
        md = render_markdown({"project": {"title": "T"}})
        assert "·" not in md.split("## ")[0].replace("Studio Brief", "")

    def test_renders_the_research_date_only(self):
        md = render_markdown(payload())
        assert "Researched 2026-03-04 · StudioOps (Gemini + Parallel)" in md
        assert "10:11:12" not in md

    def test_credits_the_generator(self):
        assert render_markdown(payload()).rstrip().endswith(
            "_Generated by StudioOps — production intelligence powered by Gemini + Parallel._"
        )

    def test_ends_with_a_newline(self):
        assert render_markdown(payload()).endswith("\n")


class TestFallbackBanner:
    def test_flags_a_report_written_without_gemini(self):
        """A producer must never mistake retrieved evidence for analysis."""
        md = render_markdown(payload(report={"generated_by": "fallback"}))

        assert "> **Note:** Gemini synthesis did not run" in md
        assert "without model analysis" in md

    def test_no_banner_for_a_model_written_report(self):
        assert "Gemini synthesis did not run" not in render_markdown(payload())


class TestMarkdownSections:
    def test_renders_the_executive_summary(self):
        md = render_markdown(payload())
        assert "## Executive Summary" in md
        assert "Nigerian scripted drama is drawing global buyers." in md

    def test_renders_key_opportunities_as_bullets(self):
        assert "- Co-production with a regional streamer" in render_markdown(payload())

    def test_every_core_section_heading_is_present(self):
        md = render_markdown(payload())
        for title in report_store.SECTION_TITLES.values():
            assert f"## {title}" in md

    def test_core_headings_survive_an_empty_report(self):
        """The brief keeps its shape even when a section found nothing."""
        md = render_markdown({"report": {}})
        for title in report_store.SECTION_TITLES.values():
            assert f"## {title}" in md

    def test_renders_a_market_signal_with_metric_and_trend(self):
        md = render_markdown(payload())
        assert "### Commission volume rising (2x year on year, trend: up)" in md
        assert "Streamers doubled local orders." in md

    def test_renders_a_comparable_with_its_descriptor(self):
        md = render_markdown(payload())
        assert "### King of Boys" in md
        assert "_2018 · Crime · Nigeria_" in md

    def test_renders_an_audience_insight(self):
        md = render_markdown(payload())
        assert "- **Under-35 mobile-first viewing** Most streaming happens on phones." in md

    def test_renders_a_competitive_gap(self):
        assert "**Gap / opportunity:** Premium crime is underserved." in render_markdown(payload())

    def test_labels_an_opportunity_category(self):
        assert "### Lagos State film office _(location)_" in render_markdown(payload())

    def test_renders_a_risk_with_its_severity_and_action(self):
        md = render_markdown(payload())
        assert "### Currency volatility — High severity" in md
        assert "**Recommended action:** Price in USD where possible." in md

    def test_defaults_an_unknown_severity_to_medium(self):
        report = payload()["report"]
        report["risks"] = [{"title": "Vague risk", "severity": "catastrophic"}]
        assert "### Vague risk — Medium severity" in render_markdown({"report": report})

    def test_numbers_the_next_steps(self):
        md = render_markdown(payload())
        assert "01. **Approach regional streamers**" in md
        assert "They are buying." in md

    def test_tolerates_a_plain_string_next_step(self):
        md = render_markdown({"report": {"next_steps": ["Call the film office"]}})
        assert "01. **Call the film office**" in md

    def test_renders_evidence_gaps(self):
        md = render_markdown(payload())
        assert "## Evidence Gaps" in md
        assert "- No verified per-episode budget figures." in md

    def test_omits_optional_sections_when_empty(self):
        md = render_markdown({"report": {}})
        assert "## Executive Summary" not in md
        assert "## Key Opportunities" not in md
        assert "## Evidence Gaps" not in md
        assert "## Recommended Next Steps" not in md


class TestSectionNotes:
    def test_explains_an_empty_section(self):
        md = render_markdown(
            {
                "report": {
                    "section_notes": {
                        "risks": {
                            "insufficient_evidence": True,
                            "note": "No risk evidence was retrieved.",
                        }
                    }
                }
            }
        )
        assert "_No risk evidence was retrieved._" in md

    def test_has_a_default_note(self):
        md = render_markdown(
            {"report": {"section_notes": {"risks": {"insufficient_evidence": True}}}}
        )
        assert "_Insufficient evidence for this section._" in md

    def test_a_populated_section_gets_no_note(self):
        data = payload()
        data["report"]["section_notes"] = {
            "risks": {"insufficient_evidence": True, "note": "should not appear"}
        }
        assert "should not appear" not in render_markdown(data)


class TestCitations:
    def test_links_each_citation_to_its_source_url(self):
        md = render_markdown(payload())
        assert "Sources: [S1](https://variety.com/s1), [S2](https://variety.com/s2)" in md

    def test_every_cited_section_carries_its_trail(self):
        md = render_markdown(payload())
        assert md.count("Sources: [S") >= 6  # one per cited section

    def test_an_unresolvable_id_renders_without_a_link(self):
        """Defensive: a bare id is honest, a link to nowhere is not."""
        data = payload()
        data["report"]["market_signals"][0]["evidence_ids"] = ["S9"]
        md = render_markdown(data)

        assert "Sources: S9" in md
        assert "[S9](" not in md

    def test_no_citation_line_for_an_uncited_claim(self):
        data = payload()
        data["report"]["market_signals"] = [{"signal": "Bare signal", "detail": "d"}]
        md = render_markdown(data)

        assert "### Bare signal" in md
        assert "Sources:" not in md.split("## Comparable Projects")[0].split("### Bare signal")[1]


class TestSources:
    def test_lists_every_source_with_a_clickable_link(self):
        md = render_markdown(payload())

        assert "## Sources (2)" in md
        assert "**S1** — [Nollywood streaming surge](https://variety.com/s1)" in md
        assert "_variety.com · 2026-01-02_" in md

    def test_falls_back_to_the_url_as_link_text(self):
        data = payload()
        data["report"]["sources"] = [source("S1", title=None)]
        assert "**S1** — [https://variety.com/s1](https://variety.com/s1)" in render_markdown(data)

    def test_includes_the_source_snippet(self):
        assert "Nigerian scripted commissions rose sharply." in render_markdown(payload())

    def test_truncates_a_long_snippet(self):
        data = payload()
        data["report"]["sources"] = [source("S1", snippet="x" * 500)]
        md = render_markdown(data)

        assert "x" * 280 + "…" in md
        assert "x" * 281 not in md

    def test_omits_the_section_with_no_sources(self):
        assert "## Sources" not in render_markdown({"report": {}})


class TestResearchTrail:
    def test_tabulates_every_planned_query(self):
        md = render_markdown(payload())

        assert "## Research Trail" in md
        assert "| Category | Query | Results | Status |" in md
        assert "| comparables | Nollywood crime thriller series streaming | 3 | ok |" in md

    def test_marks_a_failed_search(self):
        """A silently dropped query would overstate the report's coverage."""
        md = render_markdown(payload())
        assert "| market | Nigeria television market size | 0 | failed |" in md

    def test_names_the_plan_author_and_reasoning(self):
        md = render_markdown(payload())
        assert "_Plan generated by: gemini_" in md
        assert "The project needs comparables and buyer appetite." in md

    def test_escapes_a_pipe_in_a_query(self):
        """An unescaped pipe would break the table row."""
        data = payload()
        data["plan"]["tasks"] = [{"category": "market", "query": "a | b", "result_count": 1}]
        assert "| a \\| b |" in render_markdown(data)

    def test_omits_the_trail_with_no_plan(self):
        assert "## Research Trail" not in render_markdown({"report": {}})


class TestMetadataFooter:
    def test_reports_the_run_metrics(self):
        md = render_markdown(payload())
        assert (
            "Queries run: 2 · Sources reviewed: 5 · Unique sources: 2 · Total time: 4200 ms"
        ) in md

    def test_lists_warnings(self):
        data = payload(research_metadata={"warnings": ["Gemini synthesis unavailable"]})
        md = render_markdown(data)

        assert "**Warnings**" in md
        assert "- Gemini synthesis unavailable" in md

    def test_omits_the_warning_block_when_clean(self):
        assert "**Warnings**" not in render_markdown(payload())

    def test_omits_the_footer_with_no_metadata(self):
        assert "Queries run:" not in render_markdown({"report": {}})


class TestRobustness:
    def test_renders_an_empty_payload(self):
        md = render_markdown({})
        assert md.startswith("# Studio Brief — Studio Brief")

    def test_survives_null_sections(self):
        data = {
            "report": {
                "market_signals": None,
                "comparable_titles": None,
                "risks": None,
                "sources": None,
            }
        }
        assert "## Risks & Considerations" in render_markdown(data)
