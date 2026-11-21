import asyncio
from pathlib import Path
import httpx
from app.core.config import settings
from app.providers.interfaces import TTSProvider


class ElevenLabsTTSProvider(TTSProvider):
    async def synthesize(self, text: str, voice: str, output_path: Path, rate: str = "+0%") -> Path:
        if not settings.elevenlabs_api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is required for ElevenLabs speech synthesis.")
        voice_id = settings.elevenlabs_voice_id or voice
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": settings.elevenlabs_api_key, "Accept": "audio/mpeg", "Content-Type": "application/json"}
        payload = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "speed": max(0.7, min(1.2, 1 + int(rate.replace('%', '')) / 100))}}
        async with httpx.AsyncClient(timeout=90) as client:
            for attempt in range(3):
                try:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(response.content)
                    return output_path
                except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError):
                    if attempt == 2:
                        raise RuntimeError("ElevenLabs speech synthesis failed.") from None
                    await asyncio.sleep(0.5 * (2 ** attempt))
        raise RuntimeError("ElevenLabs speech synthesis failed.")
