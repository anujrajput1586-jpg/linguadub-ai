import subprocess
from pathlib import Path
from app.services.media import MediaError, media_tool


def probe_audio_duration(path: Path) -> float:
    ffprobe = media_tool("ffprobe")
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise MediaError("AUDIO_PROBE_FAILED", "Could not inspect generated speech audio.")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise MediaError("AUDIO_PROBE_FAILED", "Generated speech duration is invalid.") from exc


def atempo_chain(factor: float) -> str:
    if factor <= 0:
        raise ValueError("Tempo factor must be positive.")
    parts = []
    remaining = factor
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    parts.append(f"atempo={remaining:.5f}")
    return ",".join(parts)


def fit_audio_to_slot(source: Path, destination: Path, slot_seconds: float) -> Path:
    if slot_seconds <= 0:
        raise ValueError("Audio slot must be positive.")
    ffmpeg = media_tool("ffmpeg")
    duration = probe_audio_duration(source)
    tempo = max(1.0, duration / slot_seconds)
    if tempo > 1.25001:
        raise MediaError("SEGMENT_TOO_LONG", "Generated speech is more than 25% longer than its original timing slot.")
    filters = []
    if tempo > 1.00001:
        filters.append(atempo_chain(tempo))
    filters.append(f"apad=pad_dur={slot_seconds:.3f}")
    filters.append(f"atrim=duration={slot_seconds:.3f}")
    result = subprocess.run([ffmpeg, "-y", "-i", str(source), "-af", ",".join(filters), "-ac", "1", "-ar", "24000", str(destination)], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise MediaError("AUDIO_FIT_FAILED", "Could not fit generated speech to the original segment timing.")
    return destination
