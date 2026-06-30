from __future__ import annotations

from pathlib import Path

import pytest

from sirna_offtarget.execution.exceptions import LockError
from sirna_offtarget.execution.locking import FileLock


def test_lock_prevents_second_writer(tmp_path: Path) -> None:
    lock_path = tmp_path / "run.lock"
    with (
        FileLock(lock_path, timeout_seconds=0, stale_seconds=3600),
        pytest.raises(LockError),
        FileLock(lock_path, timeout_seconds=0, stale_seconds=3600),
    ):
        pass
