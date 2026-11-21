import re
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.languages import LANGUAGES
from app.models.entities import Project, Segment
from app.providers.factory import get_tts_provider
from app.services.audio_timing import fit_audio_to_slot, probe_audio_duration
from app.services.media import media_tool


def shorten_for_slot(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    shortened = text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:")
    return (shortened or text[:max_chars]).rstrip(".!?。！？") + "…"


async def synthesize_segment(segment: Segment, project: Project, voice: str | None = None, speed: float = 1.0) -> Path:
    text = (segment.translated_text or "").strip()
    if not text:
        raise ValueError(f"Segment {segment.id} has no translated text.")
    selected_voice = voice or LANGUAGES[project.target_language]["voice"]
    rate = f"{round((speed - 1) * 100):+d}%"
    output_dir = settings.storage_dir / "segments" / str(project.id)
    output_dir.mkdir(parents=True, exist_ok=True)
    spoken_path = output_dir / f"{segment.id}.mp3"
    fitted_path = output_dir / f"{segment.id}.wav"
    provider = get_tts_provider()
    await provider.synthesize(text, selected_voice, spoken_path, rate)
    duration = max(0.01, segment.end - segment.start)
    generated_duration = probe_audio_duration(spoken_path)
    if generated_duration / duration > 1.25:
        # Shorten once proportionally, then use atempo for the remaining small overrun.
        ratio = duration * 1.25 / generated_duration
        shorter = shorten_for_slot(text, max(1, int(len(text) * ratio)))
        if shorter == text:
            raise ValueError(f"Segment {segment.id} cannot fit its available timing slot.")
        segment.translated_text = shorter
        await provider.synthesize(shorter, selected_voice, spoken_path, rate)
    fit_audio_to_slot(spoken_path, fitted_path, duration)
    segment.audio_path = str(fitted_path.resolve())
    return fitted_path


async def preview_segment(db: Session, project: Project, segment: Segment, voice: str | None = None, speed: float = 1.0) -> Path:
    text = (segment.translated_text or "").strip()
    if not text:
        raise ValueError("Translate this segment before generating its voice preview.")
    output = settings.storage_dir / "segments" / str(project.id) / f"preview-{segment.id}.mp3"
    selected_voice = voice or LANGUAGES[project.target_language]["voice"]
    await get_tts_provider().synthesize(text, selected_voice, output, f"{round((speed - 1) * 100):+d}%")
    return output


def ensure_audio_dependencies() -> None:
    media_tool("ffmpeg")
    media_tool("ffprobe")
