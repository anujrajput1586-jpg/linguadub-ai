import shutil
from fastapi import APIRouter
from app.core.config import settings
from app.core.languages import LANGUAGES
from app.providers.wav2lip import LocalWav2LipProvider

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/languages")
def languages():
    return {"source": [{"code": "auto", "name": "Auto Detect"}, *[{"code": code, "name": item["name"]} for code, item in LANGUAGES.items()]], "target": [{"code": code, "name": item["name"]} for code, item in LANGUAGES.items()]}


@router.get("/voices")
def voices():
    return [{"language": code, "language_name": item["name"], "voice_id": item["voice"], "gender": "female", "provider": settings.tts_provider} for code, item in LANGUAGES.items()]


@router.get("/system/capabilities")
def capabilities():
    try:
        import torch
        gpu = bool(torch.cuda.is_available())
    except ImportError:
        gpu = False
    lipsync_available, lipsync_reason = LocalWav2LipProvider().available()
    return {"ffmpeg": shutil.which("ffmpeg") is not None, "ffprobe": shutil.which("ffprobe") is not None, "gpu": gpu, "stt_provider": settings.stt_provider, "translation_provider": settings.translation_provider, "tts_provider": settings.tts_provider, "lipsync_available": lipsync_available, "lipsync_reason": lipsync_reason}
