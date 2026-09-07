"""Evidence processing: dedup across queries, scoring, and citation ids."""

from __future__ import annotations

from backend.models.research import SearchTask
from backend.services.evidence import (
    MIN_USEFUL_CHARS,
    process_evidence,
    score_relevance,
)


def task(task_id: str, category: str = "market", query: str = "a query") -> SearchTask:
    return SearchTask(id=task_id, category=category, question="Why?", query=query)


def source(url: str, title: str = "Title", text: str = "", date: str = None) -> dict:
    return {
        "url": url,
        "title": title,
        "publisher": None,
        "published_date": date,
        "snippet": text,
        "excerpts": [text] if text else [],
    }


LONG = "Nollywood streaming production box office audience data. " * 30


class TestProcessEvidence:
    def test_assigns_sequential_citation_ids_in_relevance_order(self):
        evidence, _ = process_evidence(
            [
                (
                    task("t1"),
                    [
                        source("https://randomblog.example/x", text="short " * 30),
                        source("https://variety.com/a", text=LONG, date="2026-02-01"),
                    ],
                )
            ]
        )

        assert [e.id for e in evidence] == ["S1", "S2"]
        # The industry source with more text outranks the blog.
        assert evidence[0].url == "https://variety.com/a"
        assert evidence[0].relevance > evidence[1].relevance

    def test_merges_the_same_url_found_by_two_queries(self):
        shared = "https://deadline.com/story"
        evidence, task_ids = process_evidence(
            [
                (task("t1", "market", "market query"), [source(shared, text=LONG)]),
                (task("t2", "audience", "audience query"), [source(shared, text=LONG)]),
            ]
        )

        assert len(evidence) == 1
        item = evidence[0]
        assert set(item.categories) == {"market", "audience"}
        assert set(item.queries) == {"market query", "audience query"}
        # Both tasks point at the same evidence id.
        assert task_ids["t1"] == task_ids["t2"] == ["S1"]

    def test_corroboration_across_queries_raises_relevance(self):
        url = "https://someblog.example/post"
        single, _ = process_evidence([(task("t1", query="q1"), [source(url, text=LONG)])])
        double, _ = process_evidence(
            [
                (task("t1", query="q1"), [source(url, text=LONG)]),
                (task("t2", query="q2"), [source(url, text=LONG)]),
            ]
        )
        assert double[0].relevance > single[0].relevance

    def test_merges_distinct_excerpts_from_repeat_hits(self):
        url = "https://variety.com/a"
        first = source(url, text="First body of retrieved text. " * 5)
        second = source(url, text="Second body of retrieved text. " * 5)
        evidence, _ = process_evidence(
            [(task("t1", query="q1"), [first]), (task("t2", query="q2"), [second])]
        )

        assert len(evidence[0].excerpts) == 2
        assert "First body" in evidence[0].snippet
        assert "Second body" in evidence[0].snippet

    def test_backfills_a_missing_publication_date(self):
        url = "https://variety.com/a"
        evidence, _ = process_evidence(
            [
                (task("t1", query="q1"), [source(url, text=LONG)]),
                (task("t2", query="q2"), [source(url, text=LONG, date="2026-03-04")]),
            ]
        )
        assert evidence[0].published_date == "2026-03-04"

    def test_drops_sources_with_no_retrieved_text(self):
        """A source with no page text gives the synthesizer nothing to cite."""
        evidence, task_ids = process_evidence(
            [
                (
                    task("t1"),
                    [
                        source("https://empty.example/a", text=""),
                        source("https://variety.com/a", text=LONG),
                    ],
                )
            ]
        )

        assert [e.url for e in evidence] == ["https://variety.com/a"]
        assert task_ids["t1"] == ["S1"]

    def test_skips_results_without_a_url(self):
        evidence, _ = process_evidence([(task("t1"), [source("", text=LONG)])])
        assert evidence == []

    def test_task_map_is_present_even_for_an_empty_task(self):
        evidence, task_ids = process_evidence([(task("t1"), [])])
        assert evidence == []
        assert task_ids == {"t1": []}

    def test_respects_the_max_sources_cap(self):
        results = [source(f"https://site{i}.example/a", text=LONG) for i in range(30)]
        evidence, _ = process_evidence([(task("t1"), results)], max_sources=10)
        assert len(evidence) == 10
        assert [e.id for e in evidence] == [f"S{i}" for i in range(1, 11)]

    def test_derives_the_publisher_from_the_url(self):
        evidence, _ = process_evidence(
            [(task("t1"), [source("https://www.guardian.ng/story", text=LONG)])]
        )
        assert evidence[0].publisher == "guardian.ng"

    def test_falls_back_to_the_domain_for_a_missing_title(self):
        evidence, _ = process_evidence(
            [(task("t1"), [source("https://variety.com/a", title="", text=LONG)])]
        )
        assert evidence[0].title == "variety.com"

    def test_decodes_html_entities_in_text(self):
        evidence, _ = process_evidence(
            [
                (
                    task("t1"),
                    [
                        source(
                            "https://variety.com/a",
                            title="Nollywood&#x27;s rise",
                            text="Netflix&#39;s slate &amp; Showmax. " * 10,
                        )
                    ],
                )
            ]
        )
        assert evidence[0].title == "Nollywood's rise"
        assert "Netflix's slate & Showmax" in evidence[0].snippet
        assert "&#39;" not in evidence[0].snippet


class TestScoreRelevance:
    def test_industry_domains_outrank_unknown_ones(self):
        item_a = {"url": "https://variety.com/a"}
        item_b = {"url": "https://unknown-blog.example/a"}
        assert score_relevance(item_a, LONG) > score_relevance(item_b, LONG)

    def test_press_release_aggregators_are_penalized(self):
        """These dominate naive web search and carry no analysis."""
        junk = {"url": "https://www.prnewswire.com/release"}
        ordinary = {"url": "https://unknown-blog.example/a"}
        assert score_relevance(junk, LONG) < score_relevance(ordinary, LONG)

    def test_more_retrieved_text_scores_higher(self):
        item = {"url": "https://unknown-blog.example/a"}
        assert score_relevance(item, LONG) > score_relevance(item, "x" * 100)

    def test_thin_text_is_penalized(self):
        item = {"url": "https://unknown-blog.example/a"}
        assert score_relevance(item, "x" * (MIN_USEFUL_CHARS - 10)) < 0.35

    def test_film_vocabulary_raises_the_score(self):
        item = {"url": "https://unknown-blog.example/a"}
        on_topic = "box office streaming series production audience distribution " * 10
        off_topic = "quarterly logistics supply chain warehouse throughput " * 10
        assert score_relevance(item, on_topic) > score_relevance(item, off_topic)

    def test_a_publication_date_raises_the_score(self):
        with_date = {"url": "https://unknown-blog.example/a", "published_date": "2026-01-01"}
        without = {"url": "https://unknown-blog.example/a"}
        assert score_relevance(with_date, LONG) > score_relevance(without, LONG)

    def test_score_stays_within_bounds(self):
        best = {"url": "https://variety.com/a", "published_date": "2026-01-01"}
        worst = {"url": "https://prnewswire.com/a"}
        assert 0.0 <= score_relevance(worst, "") <= 1.0
        assert 0.0 <= score_relevance(best, LONG) <= 1.0

    def test_handles_a_subdomain_of_an_industry_publisher(self):
        item = {"url": "https://news.variety.com/a"}
        assert score_relevance(item, LONG) == score_relevance({"url": "https://variety.com/a"}, LONG)

    def test_tolerates_a_malformed_url(self):
        assert 0.0 <= score_relevance({"url": "::not a url::"}, LONG) <= 1.0
