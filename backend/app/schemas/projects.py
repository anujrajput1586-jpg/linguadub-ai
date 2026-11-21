from pydantic import BaseModel, Field


class SegmentUpdate(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    original_text: str = Field(min_length=1)
    translated_text: str | None = None
    speaker: str | None = None


class TranslateRequest(BaseModel):
    target_language: str


class DubRequest(BaseModel):
    target_language: str
    voice: str | None = None
    keep_background: bool = True
    speed: float = Field(default=1, ge=0.8, le=1.2)
    lipsync: bool = False


class ExportRequest(BaseModel):
    subtitle_mode: str = Field(default="soft", pattern="^(off|soft|burn)$")
