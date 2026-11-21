from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.entities import Job, Project
from app.services.pipeline import transcribe_project


def run_transcription(project_id: int) -> None:
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        job = db.query(Job).filter_by(project_id=project_id, kind="transcribe", status="queued").order_by(Job.id.desc()).first()
        if not project or not job:
            return
        job.status = "running"
        db.commit()
        try:
            transcribe_project(db, project)
            db.refresh(job)
            db.refresh(project)
            if job.status != "cancelled":
                job.status = "completed"
                job.step = "awaiting_review"
                db.commit()
        except Exception as exc:
            db.rollback()
            project = db.get(Project, project_id)
            job = db.get(Job, job.id)
            if project:
                project.status = "failed"
                project.error_message = str(exc)
                project.current_step = "Transcription failed"
            if job:
                job.status = "failed"
                job.error_message = str(exc)
            db.commit()
