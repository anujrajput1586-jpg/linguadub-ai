from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path, language: str | None = None) -> tuple[str | None, list[TranscriptSegment]]: ...


class TranslationProvider(ABC):
    @abstractmethod
    def translate(self, text: str, source: str, target: str, context: str = "") -> str: ...


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice: str, output_path: Path, rate: str = "+0%") -> Path: ...


class LipSyncProvider(ABC):
    @abstractmethod
    def available(self) -> tuple[bool, str]: ...


class SeparationProvider(ABC):
    @abstractmethod
    def available(self) -> tuple[bool, str]: ...
