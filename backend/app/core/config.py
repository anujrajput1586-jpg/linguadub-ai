from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LinguaDub AI"
    database_url: str = "sqlite:///../storage/linguadub.db"
    storage_dir: Path = Path("../storage")
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_mb: int = 500
    max_video_minutes: int = 10
    stt_provider: str = "faster-whisper"
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    translation_provider: str = "google"
    tts_provider: str = "edge"
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    wav2lip_repo: str | None = None
    wav2lip_checkpoint: str | None = None
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @property
    def upload_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def output_dir(self) -> Path:
        return self.storage_dir / "outputs"


settings = Settings()
