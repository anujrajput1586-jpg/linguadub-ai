from pathlib import Path
from app.core.config import settings
from app.providers.interfaces import STTProvider, TranscriptSegment


class FasterWhisperProvider(STTProvider):
    def transcribe(self, audio_path: Path, language: str | None = None) -> tuple[str | None, list[TranscriptSegment]]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("faster-whisper is not installed. Install backend requirements to transcribe.") from exc
        model = WhisperModel(settings.whisper_model, device=settings.whisper_device, compute_type="int8")
        segments, info = model.transcribe(str(audio_path), language=language, vad_filter=True, word_timestamps=True)
        transcript = [TranscriptSegment(float(item.start), float(item.end), item.text.strip()) for item in segments]
        return info.language, transcript
