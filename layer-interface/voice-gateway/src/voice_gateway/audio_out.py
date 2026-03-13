from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path


class PlaybackError(RuntimeError):
    """Raised when local playback fails."""


def play_wav(path: Path) -> float:
    candidates = [
        ["paplay", str(path)],
        ["aplay", str(path)],
    ]
    for command in candidates:
        if shutil.which(command[0]) is None:
            continue
        start = time.perf_counter()
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode == 0:
            return (time.perf_counter() - start) * 1000
        raise PlaybackError(completed.stderr.strip() or f"{command[0]} failed")
    raise PlaybackError("Neither paplay nor aplay is available")
