from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_route() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_research_route_handles_missing_runtime_config() -> None:
    payload = {
        "title": "Untitled Nigerian Crime Thriller",
        "description": "A crime thriller series for a young African streaming audience.",
        "format": "Series",
        "genre": "Crime Thriller",
        "target_audience": "Young Adults",
        "geography": "Nigeria / Africa",
    }
    response = client.post("/api/v1/research", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"completed", "failed"}
