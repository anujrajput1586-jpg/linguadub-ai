from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.entities import Job, Project
from app.services.export import export_project


def run_export(project_id: int, subtitle_mode: str) -> None:
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        job = db.query(Job).filter_by(project_id=project_id, kind="export", status="queued").order_by(Job.id.desc()).first()
        if not project or not job:
            return
        job.status = "running"
        job.step = "exporting"
        project.status = "exporting"
        project.progress = 92
        project.current_step = "Mixing audio and rendering video"
        db.commit()
        try:
            export_project(db, project, subtitle_mode)
            job.status = "completed"
            job.step = "completed"
            db.commit()
        except Exception as exc:
            db.rollback()
            project = db.get(Project, project_id)
            job = db.get(Job, job.id)
            if project:
                project.status = "failed"
                project.error_message = str(exc)
                project.current_step = "Export failed"
            if job:
                job.status = "failed"
                job.error_message = str(exc)
            db.commit()
