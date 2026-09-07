"""Prompt construction and tolerant JSON extraction from model output."""

from __future__ import annotations

import json

import pytest

from backend.agent.prompts import (
    PLANNER_SYSTEM_INSTRUCTION,
    SYNTHESIS_SYSTEM_INSTRUCTION,
    build_planner_prompt,
    build_synthesis_prompt,
    extract_json,
    planner_response_schema,
    synthesis_response_schema,
)
from backend.models.brief import ProjectBrief
from backend.models.research import RESEARCH_CATEGORIES


class TestSystemInstructions:
    def test_planner_lists_every_category(self):
        for category in RESEARCH_CATEGORIES:
            assert category in PLANNER_SYSTEM_INSTRUCTION

    def test_planner_forbids_generic_business_queries(self):
        """Generic queries burn search credit and return off-domain noise."""
        assert "generic business" in PLANNER_SYSTEM_INSTRUCTION
        assert "film/TV" in PLANNER_SYSTEM_INSTRUCTION

    def test_synthesis_states_the_anti_fabrication_rules(self):
        """These are product requirements — the report informs real budgets."""
        text = SYNTHESIS_SYSTEM_INSTRUCTION
        assert "NEVER invent" in text
        for forbidden in ("statistics", "companies", "titles", "quotes", "URLs", "citations"):
            assert forbidden in text
        assert "Do not cite a source id that was not given to you" in text

    def test_synthesis_requires_citations_per_claim(self):
        assert "evidence_ids" in SYNTHESIS_SYSTEM_INSTRUCTION

    def test_synthesis_prefers_an_honest_gap_to_a_padded_section(self):
        assert "evidence_gaps" in SYNTHESIS_SYSTEM_INSTRUCTION
        assert "honest gap" in SYNTHESIS_SYSTEM_INSTRUCTION

    def test_synthesis_separates_inference_from_evidence(self):
        assert "Inference:" in SYNTHESIS_SYSTEM_INSTRUCTION

    def test_synthesis_discounts_press_release_aggregators(self):
        assert "press-release aggregators" in SYNTHESIS_SYSTEM_INSTRUCTION


class TestPlannerPrompt:
    def test_includes_every_populated_brief_field(self):
        brief = ProjectBrief(
            title="Lagos After Dark",
            description="A crime thriller in Lagos.",
            format="Series",
            genre="Crime Thriller",
            target_audience="Young adults",
            geography="Nigeria",
            budget_tier="Mid-budget",
            production_stage="Development",
        )
        prompt = build_planner_prompt(brief)

        for value in (
            "Lagos After Dark",
            "Series",
            "Crime Thriller",
            "Young adults",
            "Nigeria",
            "Mid-budget",
            "Development",
            "A crime thriller in Lagos.",
        ):
            assert value in prompt

    def test_omits_empty_optional_fields(self):
        brief = ProjectBrief(title="T", description="d")
        prompt = build_planner_prompt(brief)

        assert "Genre:" not in prompt
        assert "Budget tier:" not in prompt

    def test_surfaces_producer_questions(self):
        brief = ProjectBrief(
            title="T",
            description="d",
            research_questions=["Which platforms are buying?", "  ", ""],
        )
        prompt = build_planner_prompt(brief)

        assert "Which platforms are buying?" in prompt
        assert prompt.count("- ") == 1


class TestSynthesisPrompt:
    def source(self, source_id="S1", **overrides):
        payload = {
            "id": source_id,
            "title": "Nollywood surges",
            "url": f"https://variety.com/{source_id}",
            "publisher": "variety.com",
            "published_date": "2026-01-02",
            "categories": ["market"],
            "content": "Retrieved page text.",
        }
        payload.update(overrides)
        return payload

    def test_renders_each_source_with_its_citation_id(self):
        prompt = build_synthesis_prompt(
            ProjectBrief(title="T", description="d"),
            [self.source("S1"), self.source("S2")],
        )

        assert "[S1]" in prompt
        assert "[S2]" in prompt
        assert "https://variety.com/S1" in prompt
        assert "Retrieved page text." in prompt
        assert "SOURCES (2 retrieved via live web search)" in prompt

    def test_marks_a_source_with_no_retrieved_text(self):
        """The model must be able to tell a thin source from a rich one."""
        prompt = build_synthesis_prompt(
            ProjectBrief(title="T", description="d"), [self.source(content="")]
        )
        assert "(no text retrieved)" in prompt

    def test_falls_back_to_the_url_as_a_heading(self):
        prompt = build_synthesis_prompt(
            ProjectBrief(title="T", description="d"), [self.source(title="")]
        )
        assert "[S1] https://variety.com/S1" in prompt

    def test_renders_publisher_date_and_categories(self):
        prompt = build_synthesis_prompt(
            ProjectBrief(title="T", description="d"), [self.source()]
        )
        assert "Meta: variety.com | 2026-01-02 | market" in prompt

    def test_omits_the_meta_line_when_nothing_is_known(self):
        prompt = build_synthesis_prompt(
            ProjectBrief(title="T", description="d"),
            [self.source(publisher=None, published_date=None, categories=[])],
        )
        assert "Meta:" not in prompt

    def test_restricts_citations_to_the_listed_ids(self):
        prompt = build_synthesis_prompt(
            ProjectBrief(title="T", description="d"), [self.source()]
        )
        assert "Cite only the source ids listed above." in prompt

    def test_handles_an_empty_source_list(self):
        prompt = build_synthesis_prompt(ProjectBrief(title="T", description="d"), [])
        assert "SOURCES (0 retrieved via live web search)" in prompt


class TestResponseSchemas:
    def test_schemas_are_json_serializable(self):
        """They are sent to the SDK as structured-output constraints."""
        json.dumps(planner_response_schema())
        json.dumps(synthesis_response_schema())

    def test_planner_schema_constrains_the_category_enum(self):
        schema = planner_response_schema()
        enum = schema["properties"]["tasks"]["items"]["properties"]["category"]["enum"]
        assert enum == list(RESEARCH_CATEGORIES)

    def test_every_cited_section_declares_evidence_ids(self):
        schema = synthesis_response_schema()
        cited_sections = (
            "comparable_titles",
            "market_signals",
            "audience_insights",
            "competitive_landscape",
            "production_opportunities",
            "risks",
        )
        for section in cited_sections:
            props = schema["properties"][section]["items"]["properties"]
            assert props["evidence_ids"]["type"] == "array"

    def test_constrains_trend_and_severity_values(self):
        schema = synthesis_response_schema()
        signals = schema["properties"]["market_signals"]["items"]["properties"]
        risks = schema["properties"]["risks"]["items"]["properties"]

        assert signals["trend"]["enum"] == ["up", "down", "flat"]
        assert risks["severity"]["enum"] == ["low", "medium", "high"]

    def test_requires_an_executive_summary(self):
        assert "executive_summary" in synthesis_response_schema()["required"]


class TestExtractJson:
    def test_parses_plain_json(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_strips_a_json_fence(self):
        assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_strips_a_bare_fence(self):
        assert extract_json('```\n{"a": 1}\n```') == {"a": 1}

    def test_recovers_json_wrapped_in_prose(self):
        """Models sometimes prepend a sentence despite the JSON mime type."""
        assert extract_json('Here is the plan:\n{"a": 1}\nHope that helps!') == {"a": 1}

    def test_recovers_the_outermost_object(self):
        assert extract_json('noise {"a": {"b": 2}} noise') == {"a": {"b": 2}}

    def test_tolerates_surrounding_whitespace(self):
        assert extract_json('\n\n  {"a": 1}  \n') == {"a": 1}

    def test_rejects_empty_input(self):
        with pytest.raises(ValueError, match="empty"):
            extract_json("")

    def test_rejects_output_with_no_object(self):
        with pytest.raises(ValueError, match="no JSON object"):
            extract_json("I cannot help with that request.")

    def test_rejects_a_top_level_array(self):
        with pytest.raises(ValueError, match="expected a JSON object"):
            extract_json("[1, 2, 3]")
