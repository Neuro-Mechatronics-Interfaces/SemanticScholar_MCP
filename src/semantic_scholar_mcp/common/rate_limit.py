"""Shared interprocess request pacing for Semantic Scholar."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from filelock import FileLock
from platformdirs import user_cache_dir

DEFAULT_MIN_INTERVAL_SECONDS = 1.05


def default_state_dir() -> Path:
    """Return the shared local state directory used by all three MCP servers."""
    override = os.getenv("SEMANTIC_SCHOLAR_MCP_STATE_DIR")
    if override:
        return Path(override).expanduser()
    return Path(user_cache_dir("semantic-scholar-mcp"))


class SharedRateLimiter:
    """A machine-local, interprocess-safe minimum-interval limiter.

    The filesystem lock is intentionally held while waiting so separate MCP
    processes cannot independently schedule requests into the same interval.
    """

    def __init__(
        self,
        *,
        min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
        state_dir: Path | None = None,
        lock_timeout_seconds: float = 120.0,
    ) -> None:
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must be >= 0.")

        self.min_interval_seconds = min_interval_seconds
        self.state_dir = state_dir or default_state_dir()
        self.lock_timeout_seconds = lock_timeout_seconds
        self.lock_path = self.state_dir / "rate-limit.lock"
        self.timestamp_path = self.state_dir / "last-request.txt"

    async def wait(self) -> None:
        """Wait until this process may begin its next upstream request."""
        await asyncio.to_thread(self._wait_sync)

    def _wait_sync(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)

        lock = FileLock(str(self.lock_path), timeout=self.lock_timeout_seconds)
        with lock:
            now = time.time()
            last_request = self._read_last_request()

            # If the wall clock moved backwards, conservatively wait one full interval.
            elapsed = max(0.0, now - last_request)
            delay = self.min_interval_seconds - elapsed
            if delay > 0:
                time.sleep(delay)

            self._write_last_request(time.time())

    def _read_last_request(self) -> float:
        try:
            return float(self.timestamp_path.read_text(encoding="utf-8").strip())
        except (FileNotFoundError, OSError, ValueError):
            return 0.0

    def _write_last_request(self, timestamp: float) -> None:
        temporary = self.timestamp_path.with_suffix(".tmp")
        temporary.write_text(f"{timestamp:.9f}\n", encoding="utf-8")
        os.replace(temporary, self.timestamp_path)