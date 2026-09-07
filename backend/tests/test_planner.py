"""Research planner: Gemini path, validation of model output, and fallback."""

from __future__ import annotations

import pytest

from backend.agent.planner import (
    MAX_TASKS,
    build_fallback_plan,
    create_research_plan,
)
from backend.integrations.gemini_client import GeminiError
from backend.models.brief import ProjectBrief

from .conftest import FakeGemini


def gemini_plan(**overrides):
    payload = {
        "reasoning": "Model reasoning about the brief.",
        "tasks": [
            {
                "category": "comparables",
                "question": "Which Nigerian crime series are comparable?",
                "query": "Nigerian crime thriller series comparable titles 2025",
                "priority": 1,
            },
            {
                "category": "market",
                "question": "How big is the market?",
                "query": "Nigeria television market size 2026",
                "priority": 2,
            },
        ],
    }
    payload.update(overrides)
    return payload


class TestGeminiPath:
    async def test_uses_gemini_when_configured(self, brief):
        fake = FakeGemini([gemini_plan()])
        plan = await create_research_plan(brief, gemini=fake)

        assert plan.generated_by == "gemini"
        assert plan.reasoning == "Model reasoning about the brief."
        assert plan.queries == [
            "Nigerian crime thriller series comparable titles 2025",
            "Nigeria television market size 2026",
        ]
        assert len(fake.calls) == 1

    async def test_prompt_carries_the_brief(self, brief):
        fake = FakeGemini([gemini_plan()])
        await create_research_plan(brief, gemini=fake)

        prompt = fake.calls[0]["prompt"]
        assert "Lagos After Dark" in prompt
        assert "Crime Thriller" in prompt
        assert "Nigeria" in prompt

    async def test_skips_gemini_when_unconfigured(self, brief):
        fake = FakeGemini(configured=False)
        plan = await create_research_plan(brief, gemini=fake)

        assert plan.generated_by == "fallback"
        assert fake.calls == []

    async def test_falls_back_when_gemini_errors(self, brief):
        fake = FakeGemini(raise_error=GeminiError("quota exhausted"))
        plan = await create_research_plan(brief, gemini=fake)

        assert plan.generated_by == "fallback"
        assert len(plan.tasks) >= 4

    async def test_falls_back_when_gemini_returns_too_few_tasks(self, brief):
        fake = FakeGemini([gemini_plan(tasks=[{"query": "one thing"}])])
        plan = await create_research_plan(brief, gemini=fake)

        assert plan.generated_by == "fallback"


class TestModelOutputValidation:
    async def test_drops_tasks_without_a_query(self, brief):
        payload = gemini_plan()
        payload["tasks"].append({"category": "market", "question": "no query here"})
        plan = await create_research_plan(brief, gemini=FakeGemini([payload]))

        assert len(plan.tasks) == 2

    async def test_deduplicates_equivalent_queries(self, brief):
        payload = gemini_plan()
        payload["tasks"].append(
            {"category": "market", "query": "Nigeria Television Market Size, 2026!"}
        )
        plan = await create_research_plan(brief, gemini=FakeGemini([payload]))

        assert len(plan.tasks) == 2

    async def test_unknown_category_degrades_to_other(self, brief):
        payload = gemini_plan(
            tasks=[
                {"category": "vibes", "query": "a", "question": "q"},
                {"category": "MARKET", "query": "b", "question": "q"},
            ]
        )
        plan = await create_research_plan(brief, gemini=FakeGemini([payload]))

        assert [t.category for t in plan.tasks] == ["other", "market"]

    async def test_clamps_priority_and_orders_by_it(self, brief):
        payload = gemini_plan(
            tasks=[
                {"category": "market", "query": "low priority", "priority": 99},
                {"category": "market", "query": "high priority", "priority": -4},
            ]
        )
        plan = await create_research_plan(brief, gemini=FakeGemini([payload]))

        assert [t.priority for t in plan.tasks] == [1, 5]
        assert plan.tasks[0].query == "high priority"
        # Ids are reassigned to reflect execution order.
        assert [t.id for t in plan.tasks] == ["t1", "t2"]

    async def test_tolerates_a_non_numeric_priority(self, brief):
        payload = gemini_plan(
            tasks=[
                {"category": "market", "query": "a", "priority": "urgent"},
                {"category": "market", "query": "b", "priority": 1},
            ]
        )
        plan = await create_research_plan(brief, gemini=FakeGemini([payload]))
        assert {t.priority for t in plan.tasks} == {1, 3}

    async def test_caps_the_task_count(self, brief):
        payload = gemini_plan(
            tasks=[
                {"category": "market", "query": f"query number {i}", "priority": 1}
                for i in range(20)
            ]
        )
        plan = await create_research_plan(brief, gemini=FakeGemini([payload]))

        assert len(plan.tasks) == MAX_TASKS

    async def test_ignores_non_dict_task_entries(self, brief):
        payload = gemini_plan()
        payload["tasks"] = ["just a string", None] + payload["tasks"]
        plan = await create_research_plan(brief, gemini=FakeGemini([payload]))
        assert len(plan.tasks) == 2

    async def test_question_defaults_to_the_query(self, brief):
        payload = gemini_plan(
            tasks=[
                {"category": "market", "query": "alpha"},
                {"category": "market", "query": "beta"},
            ]
        )
        plan = await create_research_plan(brief, gemini=FakeGemini([payload]))
        assert plan.tasks[0].question == "alpha"


class TestFallbackPlan:
    def test_covers_the_core_research_categories(self, brief):
        plan = build_fallback_plan(brief)
        categories = {t.category for t in plan.tasks}

        assert {"comparables", "market", "audience", "competition"} <= categories
        assert 4 <= len(plan.tasks) <= MAX_TASKS
        assert plan.generated_by == "fallback"

    def test_queries_stay_in_the_film_domain(self, brief):
        """A generic business query would waste search credit and return noise."""
        film_vocabulary = (
            "film",
            "series",
            "television",
            "box office",
            "streaming",
            "production",
            "audience",
            "distribution",
            "industry",
            "viewership",
        )
        for task in build_fallback_plan(brief).tasks:
            assert any(word in task.query.lower() for word in film_vocabulary), task.query

    def test_anchors_queries_to_the_brief(self, brief):
        queries = " ".join(build_fallback_plan(brief).queries).lower()
        assert "nigeria" in queries
        assert "crime thriller" in queries
        assert "series" in queries

    def test_producer_questions_are_searched_first(self):
        brief = ProjectBrief(
            title="Lagos After Dark",
            description="A Nigerian crime thriller series.",
            format="Series",
            genre="Crime Thriller",
            geography="Nigeria",
            research_questions=[
                "What are comparable recent Nigerian crime thrillers and how did they perform?"
            ],
        )
        plan = build_fallback_plan(brief)
        first = plan.tasks[0].query.lower()

        assert "comparable recent nigerian crime thrillers" in first
        # The interrogative framing and trailing clause are stripped — search
        # engines match noun phrases, not questions.
        assert not first.startswith("what")
        assert "how did they perform" not in first
        assert "?" not in plan.tasks[0].query

    def test_question_context_is_not_duplicated(self):
        brief = ProjectBrief(
            title="Doc",
            description="A documentary.",
            format="Documentary",
            genre="Documentary",
            geography="Kenya",
            research_questions=["Which Kenya documentary festivals accept submissions?"],
        )
        query = build_fallback_plan(brief).tasks[0].query.lower()
        assert query.count("kenya") == 1
        assert query.count("documentary") == 1

    def test_no_duplicate_queries(self, brief):
        queries = build_fallback_plan(brief).queries
        assert len(queries) == len(set(queries))

    def test_handles_a_sparse_brief(self):
        """Format, genre and geography are all optional in the intake form."""
        brief = ProjectBrief(
            title="Untitled Project",
            description="A story about Afrobeats artists touring Europe.",
        )
        plan = build_fallback_plan(brief)

        assert len(plan.tasks) >= 4
        for task in plan.tasks:
            assert task.query.strip()
            assert "  " not in task.query
            assert task.query == task.query.strip()

    def test_maps_format_to_industry_vocabulary(self):
        cases = {
            "TV Series": "series",
            "Feature Film": "film",
            "Documentary": "documentary",
            "Short": "short film",
        }
        for fmt, expected in cases.items():
            brief = ProjectBrief(title="X", description="A project.", format=fmt)
            assert expected in " ".join(build_fallback_plan(brief).queries).lower()

    def test_every_task_has_a_progress_label(self, brief):
        for task in build_fallback_plan(brief).tasks:
            assert task.label().startswith("Searching")
