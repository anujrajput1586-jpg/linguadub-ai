import time
import httpx
from pathlib import Path
from app.core.config import settings
from app.providers.interfaces import STTProvider, TranscriptSegment


class OpenAIWhisperProvider(STTProvider):
    def transcribe(self, audio_path: Path, language: str | None = None) -> tuple[str | None, list[TranscriptSegment]]:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI Whisper provider.")
        data = {"model": "whisper-1", "response_format": "verbose_json", "timestamp_granularities[]": "segment"}
        if language:
            data["language"] = language
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        for attempt in range(3):
            try:
                with audio_path.open("rb") as audio:
                    response = httpx.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, data=data, files={"file": (audio_path.name, audio, "audio/wav")}, timeout=180)
                response.raise_for_status()
                result = response.json()
                segments = [TranscriptSegment(float(item["start"]), float(item["end"]), item["text"].strip()) for item in result.get("segments", [])]
                return result.get("language"), segments
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError, KeyError, ValueError):
                if attempt == 2:
                    raise RuntimeError("OpenAI Whisper transcription request failed.") from None
                time.sleep(0.5 * (2 ** attempt))
        raise RuntimeError("OpenAI Whisper transcription request failed.")
