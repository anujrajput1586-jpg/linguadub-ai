from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.entities import Project


def get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND", "message": "Project not found."})
    return project
