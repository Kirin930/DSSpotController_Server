from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    return f"sha256:{digest}"


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"
