import asyncio
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import Base
from app.models.entities import Project
from app.providers.edge_tts import EdgeTTSProvider
from app.services.dubbing import synthesize_segment
from app.services.export import export_project
from app.services.media import probe_video
from app.services.pipeline import transcribe_project
from app.services.translation import translate_project


pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.getenv("RUN_MEDIA_INTEGRATION") != "1"
    or not shutil.which("ffmpeg")
    or not shutil.which("ffprobe")
    or importlib.util.find_spec("faster_whisper") is None,
    reason="Set RUN_MEDIA_INTEGRATION=1 and install FFmpeg/ffprobe plus faster-whisper to run the real media pipeline.",
)]


def test_free_provider_pipeline_on_generated_short_video(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path)
    monkeypatch.setattr(settings, "stt_provider", "faster-whisper")
    monkeypatch.setattr(settings, "whisper_model", "tiny")
    monkeypatch.setattr(settings, "translation_provider", "google")
    monkeypatch.setattr(settings, "tts_provider", "edge")
    spoken = tmp_path / "source.mp3"
    asyncio.run(EdgeTTSProvider().synthesize("Check the spindle alignment before starting the machine.", "en-US-AriaNeural", spoken))
    source_video = tmp_path / "demo.mp4"
    subprocess.run([
        shutil.which("ffmpeg"), "-y", "-f", "lavfi", "-i", "color=c=black:s=640x360:r=24:d=12",
        "-i", str(spoken), "-filter_complex", "[1:a]apad=pad_dur=10[audio]", "-map", "0:v:0", "-map", "[audio]",
        "-t", "12", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(source_video),
    ], check=True, capture_output=True, timeout=120)
    media = probe_video(source_video)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(title="Pipeline demo", source_path=str(source_video), source_language="en", target_language="hi", duration_seconds=media["duration"], file_size=source_video.stat().st_size)
        db.add(project)
        db.commit()
        transcribe_project(db, project)
        assert project.segments and project.detected_language == "en"
        translate_project(db, project)
        for segment in project.segments:
            asyncio.run(synthesize_segment(segment, project))
        output = export_project(db, project)
        assert output.is_file() and output.stat().st_size > 0
        assert (settings.output_dir / str(project.id) / "target.srt").is_file()
