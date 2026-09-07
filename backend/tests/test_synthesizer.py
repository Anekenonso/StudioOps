"""Report synthesis, and the citation validation that blocks fabrication.

The build spec forbids inventing statistics, titles, companies, quotes, URLs or
citations. Enforcement happens in `_report_from_model_output`: a citation id the
model made up is dropped, and a claim left with no valid citation is discarded
rather than published uncited. These tests pin that behaviour down, because a
regression here would let hallucinated findings reach a producer unmarked.
"""

from __future__ import annotations

import pytest

from backend.agent.synthesizer import (
    build_empty_report,
    build_fallback_report,
    synthesize_report,
)
from backend.integrations.gemini_client import GeminiError
from backend.models.research import (
    Evidence,
    ResearchContext,
    ResearchMetadata,
    ResearchPlan,
    SearchTask,
    TaskResult,
)

from .conftest import FakeGemini


def make_context(
    evidence_count: int = 3, failed: int = 0, categories: list[str] | None = None
) -> ResearchContext:
    plan = ResearchPlan(
        reasoning="test plan",
        tasks=[SearchTask(id="t1", category="market", question="Q?", query="q")],
        generated_by="gemini",
    )
    evidence = [
        Evidence(
            id=f"S{i}",
            title=f"Source {i}",
            url=f"https://variety.com/{i}",
            publisher="variety.com",
            published_date="2026-01-0{}".format(i),
            snippet=f"Retrieved body text for source {i}. " * 5,
            excerpts=[f"Retrieved body text for source {i}. " * 5],
            categories=categories or ["market"],
            queries=["q"],
            relevance=0.8,
        )
        for i in range(1, evidence_count + 1)
    ]
    task_results = [TaskResult(task=plan.tasks[0], result_count=evidence_count)]
    for i in range(failed):
        task_results.append(
            TaskResult(
                task=SearchTask(id=f"f{i}", category="audience", question="Q?", query="q"),
                error="timeout",
            )
        )
    return ResearchContext(
        plan=plan,
        evidence=evidence,
        task_results=task_results,
        metadata=ResearchMetadata(unique_sources=evidence_count),
    )


def model_report(**overrides) -> dict:
    payload = {
        "executive_summary": "Nigerian crime drama demand is rising.",
        "key_opportunities": ["Partner with a Lagos production house"],
        "comparable_titles": [
            {
                "title": "Shanty Town",
                "year": "2023",
                "genre": "Crime",
                "market": "Nigeria",
                "insight": "Charted globally on Netflix.",
                "evidence_ids": ["S1"],
            }
        ],
        "market_signals": [
            {
                "signal": "Local commissions increasing",
                "detail": "Streamers expanded Nigerian slates.",
                "metric": "12 titles",
                "trend": "up",
                "evidence_ids": ["S2"],
            }
        ],
        "audience_insights": [
            {"insight": "Diaspora demand is strong", "detail": "d", "evidence_ids": ["S1"]}
        ],
        "competitive_landscape": [
            {
                "observation": "Few premium local thrillers",
                "detail": "d",
                "gap_or_opportunity": "Premium tier is open",
                "evidence_ids": ["S3"],
            }
        ],
        "production_opportunities": [
            {
                "title": "Lagos State Film Office",
                "category": "location",
                "detail": "d",
                "evidence_ids": ["S2"],
            }
        ],
        "risks": [
            {
                "title": "Piracy exposure",
                "severity": "high",
                "explanation": "e",
                "recommended_action": "a",
                "evidence_ids": ["S1"],
            }
        ],
        "next_steps": [{"step": "Commission a budget", "rationale": "r"}],
        "evidence_gaps": ["No viewership figures found"],
    }
    payload.update(overrides)
    return payload


class TestGeminiPath:
    async def test_builds_a_report_from_model_output(self, brief):
        context = make_context()
        report = await synthesize_report(brief, context, gemini=FakeGemini([model_report()]))

        assert report.generated_by == "gemini"
        assert report.executive_summary == "Nigerian crime drama demand is rising."
        assert report.comparable_titles[0].title == "Shanty Town"
        assert report.market_signals[0].trend == "up"
        assert report.risks[0].severity == "high"
        assert report.next_steps[0].step == "Commission a budget"
        assert report.key_opportunities == ["Partner with a Lagos production house"]
        assert report.evidence_gaps == ["No viewership figures found"]

    async def test_prompt_contains_the_evidence_with_citation_ids(self, brief):
        fake = FakeGemini([model_report()])
        await synthesize_report(brief, make_context(), gemini=fake)

        prompt = fake.calls[0]["prompt"]
        assert "[S1]" in prompt
        assert "https://variety.com/1" in prompt
        assert "Lagos After Dark" in prompt

    async def test_prompt_source_count_is_bounded(self, brief):
        """Token cost per run is capped by the spec's cost-control rules."""
        from backend.agent.synthesizer import MAX_PROMPT_SOURCES

        fake = FakeGemini([model_report()])
        await synthesize_report(brief, make_context(MAX_PROMPT_SOURCES + 15), gemini=fake)

        prompt = fake.calls[0]["prompt"]
        assert f"[S{MAX_PROMPT_SOURCES}]" in prompt
        assert f"[S{MAX_PROMPT_SOURCES + 1}]" not in prompt

    async def test_falls_back_when_gemini_errors(self, brief):
        report = await synthesize_report(
            brief, make_context(), gemini=FakeGemini(raise_error=GeminiError("503"))
        )
        assert report.generated_by == "fallback"

    async def test_falls_back_when_the_summary_is_empty(self, brief):
        report = await synthesize_report(
            brief,
            make_context(),
            gemini=FakeGemini([model_report(executive_summary="   ")]),
        )
        assert report.generated_by == "fallback"

    async def test_skips_gemini_when_unconfigured(self, brief):
        fake = FakeGemini(configured=False)
        report = await synthesize_report(brief, make_context(), gemini=fake)

        assert report.generated_by == "fallback"
        assert fake.calls == []


class TestCitationValidation:
    async def test_drops_a_fabricated_citation_id(self, brief):
        context = make_context(evidence_count=2)  # only S1, S2 exist
        payload = model_report(
            comparable_titles=[
                {"title": "Real comp", "insight": "i", "evidence_ids": ["S1", "S99"]}
            ]
        )
        report = await synthesize_report(brief, context, gemini=FakeGemini([payload]))

        assert report.comparable_titles[0].evidence_ids == ["S1"]

    async def test_discards_a_claim_with_no_valid_citation(self, brief):
        """An uncited finding is a fabrication risk, so it is not published."""
        context = make_context(evidence_count=2)
        payload = model_report(
            comparable_titles=[
                {"title": "Invented film", "insight": "i", "evidence_ids": ["S42"]},
                {"title": "Sourced film", "insight": "i", "evidence_ids": ["S1"]},
            ]
        )
        report = await synthesize_report(brief, context, gemini=FakeGemini([payload]))

        assert [c.title for c in report.comparable_titles] == ["Sourced film"]

    async def test_discards_a_claim_with_no_citations_at_all(self, brief):
        payload = model_report(
            market_signals=[{"signal": "Unsourced trend", "detail": "d"}]
        )
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))

        assert report.market_signals == []

    async def test_validation_is_recorded_in_the_run_warnings(self, brief):
        context = make_context(evidence_count=2)
        payload = model_report(
            audience_insights=[{"insight": "Invented", "evidence_ids": ["S77"]}]
        )
        await synthesize_report(brief, context, gemini=FakeGemini([payload]))

        assert any("unverifiable citation" in w for w in context.metadata.warnings)

    async def test_no_warning_when_every_citation_is_valid(self, brief):
        context = make_context()
        await synthesize_report(brief, context, gemini=FakeGemini([model_report()]))
        assert context.metadata.warnings == []

    async def test_risks_may_be_reasoned_without_a_citation(self, brief):
        """Unlike sourced findings, a risk can be analytic judgement."""
        payload = model_report(
            risks=[{"title": "Currency volatility", "explanation": "e", "recommended_action": "a"}]
        )
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))

        assert report.risks[0].title == "Currency volatility"
        assert report.risks[0].evidence_ids == []

    async def test_citation_ids_are_normalized_and_deduplicated(self, brief):
        payload = model_report(
            comparable_titles=[
                {"title": "Comp", "insight": "i", "evidence_ids": [" s1 ", "S1", "s2"]}
            ]
        )
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))

        assert report.comparable_titles[0].evidence_ids == ["S1", "S2"]

    async def test_accepts_a_single_citation_as_a_string(self, brief):
        payload = model_report(
            comparable_titles=[{"title": "Comp", "insight": "i", "evidence_ids": "S1"}]
        )
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))

        assert report.comparable_titles[0].evidence_ids == ["S1"]

    async def test_every_published_claim_resolves_to_a_real_source(self, brief):
        """End-to-end invariant: no dangling citation can reach the report."""
        context = make_context(evidence_count=3)
        payload = model_report(
            comparable_titles=[
                {"title": "A", "insight": "i", "evidence_ids": ["S1", "S404"]},
                {"title": "B", "insight": "i", "evidence_ids": ["nonsense"]},
            ],
            market_signals=[{"signal": "S", "detail": "d", "evidence_ids": ["S2", "S3"]}],
        )
        report = await synthesize_report(brief, context, gemini=FakeGemini([payload]))

        valid = {e.id for e in context.evidence}
        groups = (
            report.comparable_titles
            + report.market_signals
            + report.audience_insights
            + report.competitive_landscape
            + report.production_opportunities
            + report.risks
        )
        for claim in groups:
            assert set(claim.evidence_ids) <= valid, claim


class TestFieldSanitizing:
    async def test_drops_a_claim_with_no_headline_text(self, brief):
        payload = model_report(
            comparable_titles=[{"title": "", "insight": "i", "evidence_ids": ["S1"]}]
        )
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))
        assert report.comparable_titles == []

    async def test_placeholder_values_become_none(self, brief):
        """A metric of 'unknown' must not render as if it were a real figure."""
        payload = model_report(
            comparable_titles=[
                {
                    "title": "Comp",
                    "year": "unknown",
                    "genre": "N/A",
                    "market": "",
                    "insight": "i",
                    "evidence_ids": ["S1"],
                }
            ]
        )
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))
        comp = report.comparable_titles[0]

        assert comp.year is None
        assert comp.genre is None
        assert comp.market is None

    async def test_invalid_trend_is_dropped(self, brief):
        payload = model_report(
            market_signals=[
                {"signal": "S", "detail": "d", "trend": "sideways", "evidence_ids": ["S1"]}
            ]
        )
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))
        assert report.market_signals[0].trend is None

    async def test_invalid_severity_defaults_to_medium(self, brief):
        payload = model_report(
            risks=[{"title": "R", "severity": "catastrophic", "evidence_ids": ["S1"]}]
        )
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))
        assert report.risks[0].severity == "medium"

    async def test_invalid_opportunity_category_is_dropped(self, brief):
        payload = model_report(
            production_opportunities=[
                {"title": "O", "category": "vibes", "detail": "d", "evidence_ids": ["S1"]}
            ]
        )
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))
        assert report.production_opportunities[0].category is None

    async def test_tolerates_next_steps_as_plain_strings(self, brief):
        payload = model_report(next_steps=["Do the thing", "Then the other thing"])
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))

        assert [s.step for s in report.next_steps] == ["Do the thing", "Then the other thing"]

    async def test_ignores_non_dict_rows(self, brief):
        payload = model_report(market_signals=["a string", None])
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))
        assert report.market_signals == []

    async def test_ignores_non_string_summary_list_entries(self, brief):
        payload = model_report(key_opportunities=["real", None, 42, "  "])
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))
        assert report.key_opportunities == ["real"]


class TestSectionNotes:
    async def test_empty_sections_are_marked_insufficient(self, brief):
        payload = model_report(comparable_titles=[], risks=[])
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([payload]))

        assert report.section_notes["comparable_titles"].insufficient_evidence is True
        assert report.section_notes["risks"].insufficient_evidence is True
        assert report.section_notes["comparable_titles"].note

    async def test_populated_sections_are_not_marked(self, brief):
        report = await synthesize_report(brief, make_context(), gemini=FakeGemini([model_report()]))
        assert "comparable_titles" not in report.section_notes


class TestSources:
    async def test_cited_sources_lead_the_source_list(self, brief):
        context = make_context(evidence_count=3)
        payload = model_report(
            comparable_titles=[{"title": "C", "insight": "i", "evidence_ids": ["S3"]}],
            market_signals=[],
            audience_insights=[],
            competitive_landscape=[],
            production_opportunities=[],
            risks=[],
        )
        report = await synthesize_report(brief, context, gemini=FakeGemini([payload]))

        assert report.sources[0].id == "S3"

    async def test_the_full_research_trail_is_retained(self, brief):
        """Uncited sources still document what was searched and reviewed."""
        context = make_context(evidence_count=5)
        payload = model_report(
            comparable_titles=[{"title": "C", "insight": "i", "evidence_ids": ["S1"]}],
            market_signals=[],
            audience_insights=[],
            competitive_landscape=[],
            production_opportunities=[],
            risks=[],
        )
        report = await synthesize_report(brief, context, gemini=FakeGemini([payload]))

        assert len(report.sources) == 5
        assert {s.id for s in report.sources} == {"S1", "S2", "S3", "S4", "S5"}


class TestFallbackReport:
    def test_states_plainly_that_synthesis_did_not_run(self, brief):
        report = build_fallback_report(brief, make_context())

        assert report.generated_by == "fallback"
        assert "did not run" in report.executive_summary
        assert any("without analysis" in gap for gap in report.evidence_gaps)

    def test_invents_no_analysis(self, brief):
        """The fallback may only restate retrieved evidence."""
        report = build_fallback_report(brief, make_context())

        assert report.key_opportunities == []
        assert report.risks == []
        assert report.competitive_landscape == []

    def test_every_fallback_claim_is_traceable_to_a_source(self, brief):
        context = make_context(evidence_count=4, categories=["comparables", "market"])
        report = build_fallback_report(brief, context)
        valid = {e.id for e in context.evidence}

        for claim in report.comparable_titles + report.market_signals + report.production_opportunities:
            assert claim.evidence_ids
            assert set(claim.evidence_ids) <= valid

    def test_exposes_all_retrieved_sources(self, brief):
        context = make_context(evidence_count=4)
        report = build_fallback_report(brief, context)
        assert len(report.sources) == 4

    def test_reports_failed_searches_as_a_gap(self, brief):
        report = build_fallback_report(brief, make_context(failed=2))
        assert any("searches failed" in gap for gap in report.evidence_gaps)

    def test_recommends_configuring_gemini(self, brief):
        report = build_fallback_report(brief, make_context())
        assert any("Gemini" in step.step for step in report.next_steps)


class TestEmptyReport:
    async def test_no_evidence_short_circuits_gemini(self, brief):
        context = make_context(evidence_count=0)
        fake = FakeGemini([model_report()])
        report = await synthesize_report(brief, context, gemini=fake)

        assert fake.calls == []
        assert report.generated_by == "fallback"
        assert report.sources == []

    def test_distinguishes_failed_searches_from_empty_results(self, brief):
        failed = build_empty_report(brief, make_context(evidence_count=0, failed=1))
        empty = build_empty_report(brief, make_context(evidence_count=0))

        assert "searches failed" in failed.executive_summary
        assert "no usable sources" in empty.executive_summary

    def test_asserts_no_findings(self, brief):
        report = build_empty_report(brief, make_context(evidence_count=0))

        assert report.comparable_titles == []
        assert report.market_signals == []
        assert report.risks == []
        assert report.evidence_gaps
        assert report.next_steps  # tells the producer what to do next
