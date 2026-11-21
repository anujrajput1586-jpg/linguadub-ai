from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    source_path: Mapped[str] = mapped_column(String(1024))
    output_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_language: Mapped[str] = mapped_column(String(8), default="auto")
    detected_language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    target_language: Mapped[str] = mapped_column(String(8), default="hi")
    duration_seconds: Mapped[float] = mapped_column(Float, default=0)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="uploaded", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str] = mapped_column(String(80), default="Ready to transcribe")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    keep_background: Mapped[bool] = mapped_column(Boolean, default=True)
    lipsync_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    segments: Mapped[list["Segment"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Segment(Base):
    __tablename__ = "segments"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    original_text: Mapped[str] = mapped_column(Text)
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    speaker: Mapped[str | None] = mapped_column(String(80), nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    project: Mapped[Project] = relationship(back_populates="segments")


class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_term: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    target_term: Mapped[str] = mapped_column(String(255))
    source_language: Mapped[str] = mapped_column(String(8), default="auto")
    target_language: Mapped[str] = mapped_column(String(8), default="hi")


class VoicePreset(Base):
    __tablename__ = "voice_presets"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(8))
    voice_id: Mapped[str] = mapped_column(String(120))
    gender: Mapped[str] = mapped_column(String(20), default="female")


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24), default="queued")
    step: Mapped[str] = mapped_column(String(80), default="queued")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    project: Mapped[Project] = relationship(back_populates="jobs")


class Setting(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True)
    value: Mapped[str] = mapped_column(Text)
