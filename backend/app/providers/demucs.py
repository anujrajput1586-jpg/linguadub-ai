import shutil
import subprocess
import tempfile
from pathlib import Path
from app.providers.interfaces import SeparationProvider


class DemucsSeparationProvider(SeparationProvider):
    def available(self) -> tuple[bool, str]:
        if shutil.which("demucs"):
            return True, "Demucs command is available."
        try:
            import demucs  # noqa: F401
            return True, "Demucs Python package is available."
        except ImportError:
            return False, "Demucs is not installed; export will use FFmpeg voice ducking."

    def separate_background(self, source: Path, work_dir: Path) -> Path | None:
        available, _ = self.available()
        if not available or not shutil.which("demucs"):
            return None
        result = subprocess.run(["demucs", "--two-stems=vocals", "-o", str(work_dir), str(source)], capture_output=True, text=True, timeout=1800)
        if result.returncode:
            return None
        candidates = list(work_dir.glob("**/no_vocals.wav"))
        return candidates[0] if candidates else None
