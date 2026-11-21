from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import Project
from app.core.languages import LANGUAGES

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    return {"total_videos": len(projects), "translated_minutes": round(sum(p.duration_seconds for p in projects if p.status == "completed") / 60, 1), "available_languages": len(LANGUAGES), "recent_projects": [{"id": p.id, "title": p.title, "status": p.status, "progress": p.progress, "created_at": p.created_at} for p in sorted(projects, key=lambda project: project.created_at, reverse=True)[:6]]}
