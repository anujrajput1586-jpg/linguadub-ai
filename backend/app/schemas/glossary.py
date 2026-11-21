from pydantic import BaseModel, Field


class GlossaryTermCreate(BaseModel):
    source_term: str = Field(min_length=1, max_length=255)
    target_term: str = Field(min_length=1, max_length=255)
    source_language: str = "auto"
    target_language: str = "hi"
