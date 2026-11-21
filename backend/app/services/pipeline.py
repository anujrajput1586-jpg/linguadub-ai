from pathlib import Path
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import Project, Segment
from app.providers.factory import get_stt_provider
from app.services.media import extract_audio


def transcribe_project(db: Session, project: Project) -> None:
    project.status = "extracting_audio"
    project.current_step = "Extracting audio"
    project.progress = 12
    db.commit()
    audio_path = settings.storage_dir / "audio" / f"project-{project.id}.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    extract_audio(Path(project.source_path), audio_path)
    project.status = "transcribing"
    project.current_step = "Transcribing speech"
    project.progress = 35
    db.commit()
    language, transcript = get_stt_provider().transcribe(audio_path, None if project.source_language == "auto" else project.source_language)
    project.detected_language = language
    project.segments.clear()
    project.segments.extend(Segment(start=item.start, end=item.end, original_text=item.text) for item in transcript)
    project.status = "awaiting_review"
    project.current_step = "Review transcript"
    project.progress = 55
    db.commit()
