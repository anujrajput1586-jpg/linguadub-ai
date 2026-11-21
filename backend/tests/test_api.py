from app.core.database import SessionLocal
from fastapi.testclient import TestClient
from app.main import app
from app.models.entities import Project


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


def test_source_video_is_served_inline_with_video_content_type(tmp_path):
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"video-preview-test")
    with SessionLocal() as db:
        project = Project(title="Inline video", source_path=str(video_path), file_size=video_path.stat().st_size)
        db.add(project)
        db.commit()
        project_id = project.id
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/projects/{project_id}/download/source")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("video/mp4")
            assert response.headers["content-disposition"] == "inline"
            assert response.content == b"video-preview-test"
    finally:
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if project:
                db.delete(project)
                db.commit()
