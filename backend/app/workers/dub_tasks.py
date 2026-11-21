from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.entities import Job, Project
from app.services.dubbing import ensure_audio_dependencies, synthesize_segment


async def run_dubbing(project_id: int, voice: str | None, speed: float, keep_background: bool) -> None:
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        job = db.query(Job).filter_by(project_id=project_id, kind="dub", status="queued").order_by(Job.id.desc()).first()
        if not project or not job:
            return
        job.status = "running"
        job.step = "dubbing"
        project.status = "dubbing"
        project.progress = 72
        project.current_step = "Generating translated speech"
        project.keep_background = keep_background
        db.commit()
        try:
            ensure_audio_dependencies()
            segments = sorted(project.segments, key=lambda item: item.start)
            if not segments:
                raise ValueError("Translate and review the transcript before dubbing.")
            for index, segment in enumerate(segments, start=1):
                db.refresh(job)
                db.refresh(project)
                if job.status == "cancelled":
                    return
                await synthesize_segment(segment, project, voice, speed)
                project.progress = 72 + round(18 * index / len(segments))
                db.commit()
            db.refresh(job)
            if job.status == "cancelled":
                return
            project.status = "awaiting_review"
            project.current_step = "Review generated voices"
            project.progress = 90
            job.status = "completed"
            job.step = "awaiting_review"
        except Exception as exc:
            db.rollback()
            project = db.get(Project, project_id)
            job = db.get(Job, job.id)
            if project:
                project.status = "failed"
                project.error_message = str(exc)
                project.current_step = "Dubbing failed"
            if job:
                job.status = "failed"
                job.error_message = str(exc)
            db.commit()
