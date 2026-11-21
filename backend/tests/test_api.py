from fastapi.testclient import TestClient
from app.main import app


def test_health_languages_and_glossary_api():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        languages = client.get("/api/languages").json()
        assert len(languages["source"]) == 11
        assert len(languages["target"]) == 10
        term = client.post("/api/glossary", json={"source_term": "test spindle", "target_term": "स्पिंडल", "source_language": "en", "target_language": "hi"})
        assert term.status_code == 201
        term_id = term.json()["id"]
        assert any(item["id"] == term_id for item in client.get("/api/glossary").json())
        assert client.delete(f"/api/glossary/{term_id}").json()["deleted"]
