from backend.services.evidence import EvidenceProcessor


def test_evidence_processor_prefers_highest_relevance_duplicate_url() -> None:
    processor = EvidenceProcessor()
    results = [
        {
            "title": "Lower relevance",
            "url": "https://example.com/article?x=1",
            "snippet": "first",
            "source_type": "web",
            "relevance": 0.2,
            "category": "market",
            "question": "What is the market?",
        },
        {
            "title": "Higher relevance",
            "url": "https://example.com/article/?x=1",
            "snippet": "second",
            "source_type": "web",
            "relevance": 0.9,
            "category": "market",
            "question": "What is the market?",
        },
    ]

    processed = processor.process(results)

    assert len(processed) == 1
    assert processed[0]["relevance"] == 0.9
    assert processed[0]["title"] == "Higher relevance"
    assert processed[0]["url"] == "https://example.com/article"
