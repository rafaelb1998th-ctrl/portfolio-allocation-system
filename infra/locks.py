"""Exclusive run lock via O_EXCL file creation (stale lock auto-expires)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional


class LockError(Exception):
    pass


class FileLock:
    def __init__(self, path: Path, stale_after_seconds: int = 60 * 60):
        self.path = path
        self.stale_after_seconds = stale_after_seconds
        self.fd: Optional[int] = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.path.exists():
            age = time.time() - self.path.stat().st_mtime
            if age > self.stale_after_seconds:
                self.path.unlink(missing_ok=True)
            else:
                raise LockError(f"Lock already exists: {self.path}")

        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            payload = {"pid": os.getpid(), "ts": time.time()}
            os.write(self.fd, json.dumps(payload).encode("utf-8"))
            os.fsync(self.fd)
        except FileExistsError as exc:
            raise LockError(f"Could not acquire lock: {self.path}") from exc

    def release(self) -> None:
        try:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None
        finally:
            self.path.unlink(missing_ok=True)

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        self.release()
        return False
