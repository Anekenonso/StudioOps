from backend.agent.synthesizer import synthesize_report
from backend.models.brief import ProjectBrief


def test_synthesize_report_collects_sources():
    brief = ProjectBrief(title="Test", description="desc")
    evidence_groups = [
        {"query": "q1", "results": [{"title": "T1", "url": "http://a", "snippet": "s", "source": "S1", "relevance": 0.9}]},
        {"query": "q2", "results": [{"title": "T2", "url": "http://b", "snippet": "s2", "source": "S2", "relevance": 0.8}]},
    ]

    report = synthesize_report(brief, evidence_groups)
    assert report.executive_summary
    assert len(report.sources) == 2
    assert report.comparable_titles
