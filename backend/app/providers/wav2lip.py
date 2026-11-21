import subprocess
import sys
from pathlib import Path
from app.core.config import settings
from app.providers.interfaces import LipSyncProvider


class LocalWav2LipProvider(LipSyncProvider):
    def available(self) -> tuple[bool, str]:
        try:
            import torch
        except ImportError:
            return False, "PyTorch with CUDA support is not installed."
        if not torch.cuda.is_available():
            return False, "No CUDA GPU was detected. Lip sync is disabled; export will use dubbed audio only."
        repo = Path(settings.wav2lip_repo) if settings.wav2lip_repo else None
        checkpoint = Path(settings.wav2lip_checkpoint) if settings.wav2lip_checkpoint else None
        if not repo or not (repo / "inference.py").is_file():
            return False, "Configure WAV2LIP_REPO to a local Wav2Lip checkout."
        if not checkpoint or not checkpoint.is_file():
            return False, "Configure WAV2LIP_CHECKPOINT to the local model weights."
        return True, "Local Wav2Lip and CUDA are ready."

    def synchronize(self, video: Path, audio: Path, output: Path) -> Path:
        ready, reason = self.available()
        if not ready:
            raise RuntimeError(reason)
        repo = Path(settings.wav2lip_repo or "")
        checkpoint = Path(settings.wav2lip_checkpoint or "")
        result = subprocess.run([sys.executable, str(repo / "inference.py"), "--checkpoint_path", str(checkpoint), "--face", str(video), "--audio", str(audio), "--outfile", str(output)], cwd=repo, capture_output=True, text=True, timeout=3600)
        if result.returncode or not output.is_file():
            raise RuntimeError("Wav2Lip inference failed; the dubbed video remains available without lip sync.")
        return output
