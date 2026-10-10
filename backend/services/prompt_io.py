"""Reloadable UTF-8 prompts and a process-safe, append-only inference journal."""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

_write_lock = Lock()


def read_prompt(path: str | Path) -> str:
    try:
        prompt = Path(path).read_text(encoding="utf-8-sig").strip()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"prompt file cannot be read: {path}") from exc
    if not prompt:
        raise ValueError("prompt file is empty")
    return prompt


@contextmanager
def locked_file(path: str | Path, timeout_s: float = 30):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a+b") as lock:
        lock.seek(0, 2)
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        deadline = time.monotonic() + timeout_s
        while True:
            lock.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"File lock timed out: {target}") from None
                time.sleep(0.05)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def append_output(path: str | Path, entry: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # A sibling lock file coordinates both worker processes and Windows/POSIX hosts.
    with _write_lock, locked_file(target.with_suffix(target.suffix + ".lock")):
        with target.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
