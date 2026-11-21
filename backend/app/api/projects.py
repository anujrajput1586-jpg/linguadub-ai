import asyncio
import mimetypes
import re
import uuid
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import get_project
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import Job, Project
from app.schemas.projects import DubRequest, ExportRequest, SegmentUpdate, TranslateRequest
from app.services.media import MediaError, probe_video
from app.services.translation import translate_project
from app.workers.tasks import run_transcription
from app.workers.dub_tasks import run_dubbing
from app.services.dubbing import preview_segment
from app.services.export import artifact_path
from app.workers.export_tasks import run_export
from app.providers.wav2lip import LocalWav2LipProvider

router = APIRouter(prefix="/api/projects", tags=["projects"])
ALLOWED_SUFFIXES = {".mp4", ".mov", ".avi"}


def valid_video_signature(path: Path, suffix: str) -> bool:
    with path.open("rb") as video_file:
        header = video_file.read(16)
    if suffix in {".mp4", ".mov"}:
        return len(header) >= 8 and header[4:8] == b"ftyp"
    return len(header) >= 12 and header[:4] in {b"RIFF", b"AVI "} and header[8:12] == b"AVI "


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    source_language: str = Form("auto"),
    target_language: str = Form("hi"),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, detail={"code": "UNSUPPORTED_FORMAT", "message": "Upload an MP4, MOV, or AVI video."})
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    destination = settings.upload_dir / f"{uuid.uuid4().hex}{suffix}"
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_mb * 1024 * 1024:
                    raise HTTPException(413, detail={"code": "FILE_TOO_LARGE", "message": f"Maximum upload size is {settings.max_upload_mb} MB."})
                output.write(chunk)
        if not valid_video_signature(destination, suffix):
            raise HTTPException(400, detail={"code": "INVALID_VIDEO", "message": "The file content does not match a supported video format."})
        media = await asyncio.to_thread(probe_video, destination)
        if media["duration"] <= 0 or media["duration"] > settings.max_video_minutes * 60:
            raise HTTPException(400, detail={"code": "VIDEO_DURATION_LIMIT", "message": f"Video duration must be between 0 and {settings.max_video_minutes} minutes."})
        title = Path(file.filename or "Translation").stem
        title = re.sub(r"[\x00-\x1f]", "", title)[:255] or "Translation"
        project = Project(title=title, source_path=str(destination.resolve()), source_language=source_language, target_language=target_language, duration_seconds=media["duration"], file_size=size)
        db.add(project)
        db.commit()
        db.refresh(project)
        return project_detail(project)
    except MediaError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(503, detail={"code": exc.code, "message": str(exc)}) from exc
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


def project_detail(project: Project) -> dict:
    return {
        "id": project.id, "title": project.title, "source_language": project.source_language,
        "detected_language": project.detected_language, "target_language": project.target_language,
        "duration_seconds": project.duration_seconds, "file_size": project.file_size,
        "status": project.status, "progress": project.progress, "current_step": project.current_step,
        "error_message": project.error_message, "created_at": project.created_at,
        "segments": [{"id": seg.id, "start": seg.start, "end": seg.end, "original_text": seg.original_text, "translated_text": seg.translated_text, "speaker": seg.speaker, "audio_path": seg.audio_path} for seg in project.segments],
    }


@router.get("")
def list_projects(db: Session = Depends(get_db)):
    return [project_detail(project) for project in db.query(Project).order_by(Project.created_at.desc()).all()]


@router.get("/{project_id}")
def read_project(project_id: int, db: Session = Depends(get_db)):
    return project_detail(get_project(db, project_id))


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    source = Path(project.source_path)
    db.delete(project)
    db.commit()
    source.unlink(missing_ok=True)
    return {"deleted": True}


@router.post("/{project_id}/duplicate", status_code=201)
def duplicate_project(project_id: int, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    clone = Project(
        title=f"{project.title} copy",
        source_path=project.source_path,
        source_language=project.source_language,
        target_language=project.target_language,
        duration_seconds=project.duration_seconds,
        file_size=project.file_size,
        status="uploaded",
        current_step="Ready to transcribe",
        keep_background=project.keep_background,
    )
    db.add(clone)
    db.flush()
    clone.segments.extend(
        type(segment)(start=segment.start, end=segment.end, original_text=segment.original_text, translated_text=None, speaker=segment.speaker)
        for segment in project.segments
    )
    db.commit()
    db.refresh(clone)
    return project_detail(clone)


@router.post("/{project_id}/transcribe", status_code=202)
def start_transcription(project_id: int, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if project.status in {"extracting_audio", "transcribing"}:
        raise HTTPException(409, detail={"code": "JOB_ALREADY_RUNNING", "message": "Transcription is already running."})
    project.status = "extracting_audio"
    project.progress = 5
    project.current_step = "Queued for transcription"
    project.error_message = None
    job = Job(project_id=project.id, kind="transcribe", status="queued", step="queued")
    db.add(job)
    db.commit()
    tasks.add_task(run_transcription, project.id)
    return {"job_id": job.id, "status": project.status}


@router.put("/{project_id}/segments/{segment_id}")
def update_segment(project_id: int, segment_id: int, body: SegmentUpdate, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    segment = next((item for item in project.segments if item.id == segment_id), None)
    if not segment:
        raise HTTPException(404, detail={"code": "SEGMENT_NOT_FOUND", "message": "Segment not found."})
    if body.end <= body.start:
        raise HTTPException(422, detail={"code": "INVALID_TIMING", "message": "Segment end must be after its start."})
    for key, value in body.model_dump().items():
        setattr(segment, key, value)
    db.commit()
    return {"id": segment.id, **body.model_dump()}


@router.get("/{project_id}/status")
def project_status(project_id: int, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    return {"id": project.id, "status": project.status, "progress": project.progress, "current_step": project.current_step, "error_message": project.error_message}


@router.post("/{project_id}/cancel")
def cancel_project(project_id: int, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    job = db.query(Job).filter(Job.project_id == project_id, Job.status.in_(["queued", "running"])).order_by(Job.id.desc()).first()
    if not job:
        raise HTTPException(409, detail={"code": "NO_ACTIVE_JOB", "message": "There is no active job to cancel."})
    job.status = "cancelled"
    project.status = "cancelled"
    project.current_step = "Cancelled by user"
    db.commit()
    return {"status": project.status}


@router.post("/{project_id}/retry", status_code=202)
def retry_project(project_id: int, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    failed_job = db.query(Job).filter_by(project_id=project_id, status="failed").order_by(Job.id.desc()).first()
    if not failed_job:
        raise HTTPException(409, detail={"code": "NO_FAILED_JOB", "message": "There is no failed job to retry."})
    job = Job(project_id=project_id, kind=failed_job.kind, status="queued", step="queued")
    db.add(job)
    project.status = {"transcribe": "extracting_audio", "dub": "dubbing", "export": "exporting"}.get(job.kind, "failed")
    project.current_step = "Retry queued"
    project.error_message = None
    db.commit()
    if job.kind == "transcribe":
        tasks.add_task(run_transcription, project.id)
    elif job.kind == "dub":
        tasks.add_task(run_dubbing, project.id, None, 1.0, project.keep_background)
    elif job.kind == "export":
        tasks.add_task(run_export, project.id, "soft")
    else:
        raise HTTPException(409, detail={"code": "RETRY_UNAVAILABLE", "message": "This failed step cannot be retried automatically."})
    return {"job_id": job.id, "status": project.status}


@router.post("/{project_id}/translate")
def translate(project_id: int, body: TranslateRequest, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    target_language = body.target_language
    if target_language not in {"hi", "en", "es", "fr", "de", "ja", "ko", "zh", "ar", "pt"}:
        raise HTTPException(422, detail={"code": "UNSUPPORTED_LANGUAGE", "message": "Choose a supported target language."})
    project.target_language = target_language
    try:
        translate_project(db, project)
    except ValueError as exc:
        raise HTTPException(409, detail={"code": "TRANSLATION_NOT_READY", "message": str(exc)}) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(502, detail={"code": "TRANSLATION_FAILED", "message": "The translation provider could not complete this request."}) from exc
    return project_detail(project)


@router.post("/{project_id}/segments/{segment_id}/translate")
def retranslate_segment(project_id: int, segment_id: int, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    try:
        translate_project(db, project, segment_id)
    except LookupError as exc:
        raise HTTPException(404, detail={"code": "SEGMENT_NOT_FOUND", "message": str(exc)}) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(502, detail={"code": "TRANSLATION_FAILED", "message": "The translation provider could not complete this request."}) from exc
    return project_detail(project)


@router.post("/{project_id}/dub", status_code=202)
def start_dubbing(project_id: int, body: DubRequest, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project.segments:
        raise HTTPException(409, detail={"code": "TRANSLATION_NOT_READY", "message": "Translate and review the transcript before dubbing."})
    project.status = "dubbing"
    project.current_step = "Queued for voice generation"
    project.error_message = None
    project.keep_background = body.keep_background
    lipsync_warning = None
    if body.lipsync:
        available, reason = LocalWav2LipProvider().available()
        project.lipsync_enabled = available
        if not available:
            lipsync_warning = reason
    else:
        project.lipsync_enabled = False
    job = Job(project_id=project.id, kind="dub", status="queued", step="queued")
    db.add(job)
    db.commit()
    tasks.add_task(run_dubbing, project.id, body.voice, body.speed, body.keep_background)
    return {"job_id": job.id, "status": project.status, "lipsync_warning": lipsync_warning}


@router.post("/{project_id}/segments/{segment_id}/preview-audio")
async def segment_preview(project_id: int, segment_id: int, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    segment = next((item for item in project.segments if item.id == segment_id), None)
    if not segment:
        raise HTTPException(404, detail={"code": "SEGMENT_NOT_FOUND", "message": "Segment not found."})
    try:
        audio_path = await preview_segment(db, project, segment)
    except Exception as exc:
        raise HTTPException(502, detail={"code": "TTS_FAILED", "message": "Could not generate the voice preview. Check Edge TTS connectivity and dependencies."}) from exc
    return FileResponse(audio_path, media_type="audio/mpeg", filename=audio_path.name)


@router.post("/{project_id}/export", status_code=202)
def start_export(project_id: int, body: ExportRequest, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project.segments or any(not item.audio_path for item in project.segments):
        raise HTTPException(409, detail={"code": "DUB_NOT_READY", "message": "Generate voice audio for every segment before exporting."})
    project.status = "exporting"
    project.current_step = "Queued for export"
    project.error_message = None
    job = Job(project_id=project.id, kind="export", status="queued", step="queued")
    db.add(job)
    db.commit()
    tasks.add_task(run_export, project.id, body.subtitle_mode)
    return {"job_id": job.id, "status": project.status}


@router.get("/{project_id}/download/{kind}")
def download_artifact(project_id: int, kind: str, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    try:
        path = artifact_path(project.id, kind, project)
    except ValueError as exc:
        raise HTTPException(404, detail={"code": "DOWNLOAD_NOT_FOUND", "message": str(exc)}) from exc
    if not path.is_file():
        raise HTTPException(404, detail={"code": "DOWNLOAD_NOT_READY", "message": "This download is not ready yet."})
    if kind == "source":
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return FileResponse(path, media_type=media_type, headers={"Content-Disposition": "inline"})
    return FileResponse(path, filename=path.name)
