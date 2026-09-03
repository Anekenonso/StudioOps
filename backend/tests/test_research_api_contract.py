from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_master_api_contract() -> None:
    payload = {
        "project_title": "Lagos After Dark",
        "format": "Film",
        "genre": "Crime Thriller",
        "market": "Nigeria",
        "brief": "A contemporary Nigerian crime thriller set in Lagos.",
        "research_questions": [
            "What are comparable recent titles?",
            "What market trends matter?",
            "Which production companies are relevant?",
        ],
    }
    response = client.post("/api/research", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"completed", "failed"}
    assert "project" in body or "error" in body
