import json
import subprocess
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import Project
from app.providers.demucs import DemucsSeparationProvider
from app.providers.wav2lip import LocalWav2LipProvider
from app.services.media import media_tool
from app.services.subtitles import build_srt, build_vtt


def write_dub_track(project: Project, output: Path) -> Path:
    segments = sorted(project.segments, key=lambda item: item.start)
    if not segments or any(not item.audio_path or not Path(item.audio_path).exists() for item in segments):
        raise ValueError("Generate voice audio for every segment before exporting.")
    ffmpeg = media_tool("ffmpeg")
    inputs = ["-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono:d={project.duration_seconds:.3f}"]
    filters = []
    labels = ["[0:a]"]
    for index, segment in enumerate(segments, start=1):
        inputs.extend(["-i", segment.audio_path])
        filters.append(f"[{index}:a]adelay={round(segment.start * 1000)}:all=1[seg{index}]")
        labels.append(f"[seg{index}]")
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:duration=longest:normalize=0[voice]")
    command = [ffmpeg, "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[voice]", "-t", f"{project.duration_seconds:.3f}", "-ac", "2", "-ar", "48000", str(output)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise RuntimeError("Could not assemble the translated speech track.")
    return output


def export_project(db: Session, project: Project, subtitle_mode: str = "soft") -> Path:
    if subtitle_mode not in {"off", "soft", "burn"}:
        raise ValueError("Subtitle mode must be off, soft, or burn.")
    output_dir = settings.output_dir / str(project.id)
    output_dir.mkdir(parents=True, exist_ok=True)
    dub_audio = write_dub_track(project, output_dir / "dubbed.wav")
    source_video = Path(project.source_path)
    ffmpeg = media_tool("ffmpeg")
    background = None
    if project.keep_background:
        source_audio = output_dir / "original.wav"
        extraction = subprocess.run([ffmpeg, "-y", "-i", str(source_video), "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(source_audio)], capture_output=True, text=True, timeout=600)
        if extraction.returncode:
            raise RuntimeError("Could not extract the original background audio.")
        background = DemucsSeparationProvider().separate_background(source_audio, output_dir / "separation")
    video_path = output_dir / "final.mp4"
    command = [ffmpeg, "-y", "-i", str(source_video), "-i", str(dub_audio)]
    if background:
        command.extend(["-i", str(background)])
        bg_index = 2
        bg_input = f"[{bg_index}:a]"
    else:
        bg_index = 0
        bg_input = "[0:a]"
    if project.keep_background:
        audio_filter = f"{bg_input}aresample=48000,volume=0.35[bg];[1:a]aresample=48000[voice];[bg][voice]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=250[ducked];[ducked][voice]amix=inputs=2:duration=longest:normalize=0[aout]"
    else:
        audio_filter = "[1:a]aresample=48000[aout]"
    command.extend(["-filter_complex", audio_filter, "-map", "0:v:0", "-map", "[aout]"])
    target_srt = output_dir / "target.srt"
    original_srt = output_dir / "original.srt"
    target_vtt = output_dir / "target.vtt"
    original_vtt = output_dir / "original.vtt"
    target_srt.write_text(build_srt(project.segments, True), encoding="utf-8")
    original_srt.write_text(build_srt(project.segments, False), encoding="utf-8")
    target_vtt.write_text(build_vtt(project.segments, True), encoding="utf-8")
    original_vtt.write_text(build_vtt(project.segments, False), encoding="utf-8")
    if subtitle_mode == "soft":
        subtitle_index = 3 if background else 2
        command.extend(["-i", str(target_srt), "-map", f"{subtitle_index}:s:0", "-c:s", "mov_text"])
    elif subtitle_mode == "burn":
        escaped = str(target_srt.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
        command.extend(["-vf", f"subtitles='{escaped}':force_style='FontName=Noto Sans,FontSize=18'"])
    command.extend(["-c:v", "libx264" if subtitle_mode == "burn" else "copy", "-c:a", "aac", "-shortest", str(video_path)])
    result = subprocess.run(command, capture_output=True, text=True, timeout=1800)
    if result.returncode:
        raise RuntimeError("FFmpeg could not create the final video. Check codec and subtitle font support.")
    if project.lipsync_enabled:
        try:
            synced_path = output_dir / "final-lipsync.mp4"
            video_path = LocalWav2LipProvider().synchronize(video_path, dub_audio, synced_path)
        except Exception:
            project.lipsync_enabled = False
    transcript = [{"start": item.start, "end": item.end, "original_text": item.original_text, "translated_text": item.translated_text, "speaker": item.speaker} for item in project.segments]
    (output_dir / "transcript.json").write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "transcript.txt").write_text("\n".join(item.original_text for item in project.segments), encoding="utf-8")
    project.output_path = str(video_path.resolve())
    project.status = "completed"
    project.progress = 100
    project.current_step = "Export complete"
    project.error_message = None
    db.commit()
    return video_path


def artifact_path(project_id: int, kind: str, project: Project) -> Path:
    output_dir = settings.output_dir / str(project_id)
    names = {"source": project.source_path, "video": "final.mp4", "audio": "dubbed.wav", "target-srt": "target.srt", "original-srt": "original.srt", "target-vtt": "target.vtt", "original-vtt": "original.vtt", "transcript-json": "transcript.json", "transcript-txt": "transcript.txt"}
    if kind not in names:
        raise ValueError("Unknown download type.")
    path = Path(names[kind]) if kind == "source" else output_dir / names[kind]
    if kind == "video" and project.output_path:
        path = Path(project.output_path)
    return path
