from __future__ import annotations

import json
import os
import socket
import time
from contextlib import suppress
from pathlib import Path

from sirna_offtarget.execution.exceptions import LockError


class FileLock:
    def __init__(self, path: Path, timeout_seconds: int = 300, stale_seconds: int = 3600) -> None:
        self.path = path
        self.timeout_seconds = timeout_seconds
        self.stale_seconds = stale_seconds

    def __enter__(self) -> FileLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + self.timeout_seconds
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w") as handle:
                    json.dump(
                        {
                            "pid": os.getpid(),
                            "hostname": socket.gethostname(),
                            "created_at_epoch": time.time(),
                        },
                        handle,
                    )
                return self
            except FileExistsError as exc:
                age = time.time() - self.path.stat().st_mtime
                if age > self.stale_seconds:
                    raise LockError(
                        f"stale lock detected at {self.path}; remove or override explicitly"
                    ) from exc
                if time.time() >= deadline:
                    raise LockError(f"timed out waiting for lock {self.path}") from exc
                time.sleep(0.2)

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        with suppress(FileNotFoundError):
            self.path.unlink()
