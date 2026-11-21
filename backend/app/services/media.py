import json
import shutil
import subprocess
from pathlib import Path


class MediaError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def media_tool(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise MediaError("MEDIA_TOOLS_MISSING", f"{name} is required. Install FFmpeg and ensure it is on PATH.")
    return executable


def probe_video(path: Path) -> dict:
    ffprobe = media_tool("ffprobe")
    result = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise MediaError("INVALID_VIDEO", "The uploaded video is corrupt or cannot be read.")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MediaError("INVALID_VIDEO", "The uploaded video metadata could not be read.") from exc
    streams = data.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video:
        raise MediaError("INVALID_VIDEO", "The file does not contain a video stream.")
    if not audio:
        raise MediaError("NO_AUDIO", "The video has no audio track to transcribe.")
    try:
        duration = float(data.get("format", {}).get("duration", 0))
    except (TypeError, ValueError):
        duration = 0
    return {"duration": duration, "video": video, "audio": audio}


def extract_audio(video_path: Path, output_path: Path) -> Path:
    ffmpeg = media_tool("ffmpeg")
    result = subprocess.run([ffmpeg, "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(output_path)], capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise MediaError("AUDIO_EXTRACTION_FAILED", "Could not extract audio from this video.")
    return output_path
