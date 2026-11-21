from pathlib import Path
import edge_tts
from app.providers.interfaces import TTSProvider


class EdgeTTSProvider(TTSProvider):
    async def synthesize(self, text: str, voice: str, output_path: Path, rate: str = "+0%") -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        communication = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        await communication.save(str(output_path))
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("The TTS provider returned an empty audio file.")
        return output_path
