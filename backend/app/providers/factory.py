from app.core.config import settings
from app.providers.edge_tts import EdgeTTSProvider
from app.providers.elevenlabs import ElevenLabsTTSProvider
from app.providers.gemini import GeminiTranslationProvider
from app.providers.openai_whisper import OpenAIWhisperProvider
from app.providers.translation import GoogleTranslationProvider
from app.providers.whisper import FasterWhisperProvider


def get_stt_provider():
    if settings.stt_provider.lower() == "openai":
        return OpenAIWhisperProvider()
    return FasterWhisperProvider()


def get_translation_provider():
    if settings.translation_provider.lower() == "gemini":
        return GeminiTranslationProvider()
    return GoogleTranslationProvider()


def get_tts_provider():
    if settings.tts_provider.lower() == "elevenlabs":
        return ElevenLabsTTSProvider()
    return EdgeTTSProvider()
