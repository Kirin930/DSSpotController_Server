from __future__ import annotations

import re
from pathlib import Path


FILENAME_SANITIZER = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    safe_name = Path(filename or "spot.bin").name
    safe_name = FILENAME_SANITIZER.sub("_", safe_name)
    return safe_name or "spot.bin"


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
