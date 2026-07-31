"""DSS v3 runtime state: lock, seen registry, journal, and progress files."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

from backtester.strategy_discovery.dss_config import DSSCandidate, DSSConfig

_T = TypeVar("_T", bound=DSSCandidate)


class DSSSearchRuntime:
    """Durable per-output runtime state for bounded and endless DSS runs."""

    def __init__(self, *, config: DSSConfig) -> None:
        self.config = config
        self.output = config.output
        self.lock_path = self.output / "search.lock"
        self.seen_path = self.output / "seen_candidates.jsonl"
        self.journal_path = self.output / "candidate_journal.jsonl"
        self.progress_path = self.output / "progress.json"
        self.heartbeat_path = self.output / "heartbeat.json"
        self._lock_fd: int | None = None
        self._seen = self._load_seen()

    @property
    def endless(self) -> bool:
        return self.config.n_trials is None

    def __enter__(self) -> DSSSearchRuntime:
        self.output.mkdir(parents=True, exist_ok=True)
        (self.output / "backend_state").mkdir(exist_ok=True)
        (self.output / "archive").mkdir(exist_ok=True)
        self._acquire_lock()
        self.write_heartbeat(status="running")
        return self

    def __exit__(self, exc_type: object, _exc: object, _tb: object) -> None:
        self.write_heartbeat(status="stopped" if exc_type is None else "failed")
        self._release_lock()

    def should_continue(self, generated: int) -> bool:
        return self.config.n_trials is None or generated < self.config.n_trials

    def remaining_batch(self, generated: int, default_batch_size: int) -> int:
        if self.config.n_trials is None:
            return default_batch_size
        return max(0, min(default_batch_size, self.config.n_trials - generated))

    def record_candidate(self, candidate: DSSCandidate, *, source: str) -> bool:
        candidate_hash = candidate.candidate_key
        if candidate_hash in self._seen:
            self._append_jsonl(
                self.journal_path,
                {
                    "event": "duplicate_skipped",
                    "candidate_id": candidate.candidate_id,
                    "candidate_hash": candidate_hash,
                    "source": source,
                    "ts": _utc_now(),
                },
            )
            return False
        self._seen.add(candidate_hash)
        self._append_jsonl(
            self.seen_path,
            {
                "candidate_hash": candidate_hash,
                "candidate_id": candidate.candidate_id,
                "ts": _utc_now(),
            },
        )
        self._append_jsonl(
            self.journal_path,
            {
                "event": "candidate_generated",
                "candidate_id": candidate.candidate_id,
                "candidate_hash": candidate_hash,
                "source": source,
                "candidate": candidate.to_dict(),
                "ts": _utc_now(),
            },
        )
        return True

    def mark_evaluated(self, candidate: DSSCandidate, *, promoted: bool, score: float | None) -> None:
        self._append_jsonl(
            self.journal_path,
            {
                "event": "candidate_evaluated",
                "candidate_id": candidate.candidate_id,
                "candidate_hash": candidate.candidate_key,
                "promoted": promoted,
                "score": score,
                "ts": _utc_now(),
            },
        )

    def write_progress(self, *, generated: int, evaluated: int, exported: int = 0) -> None:
        payload = {
            "status": "running",
            "generated": generated,
            "evaluated": evaluated,
            "exported": exported,
            "target": self.config.n_trials,
            "endless": self.endless,
            "updated_at": _utc_now(),
        }
        self.progress_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self.write_heartbeat(status="running")

    def write_heartbeat(self, *, status: str) -> None:
        payload = {
            "status": status,
            "pid": os.getpid(),
            "endless": self.endless,
            "updated_at": _utc_now(),
        }
        self.heartbeat_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )

    def sample_unseen(
        self,
        sampler: Callable[[str, int], _T],
        *,
        candidate_id_prefix: str,
        generation: int,
        start_index: int,
        source: str,
        max_attempts: int = 128,
    ) -> _T | None:
        for attempt in range(max_attempts):
            candidate = sampler(f"{candidate_id_prefix}_{start_index + attempt:06d}", generation)
            if candidate.candidate_key in self._seen:
                continue
            if self.record_candidate(candidate, source=source):
                return candidate
        return None

    def _load_seen(self) -> set[str]:
        seen: set[str] = set()
        if self.seen_path.exists():
            for line in self.seen_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                candidate_hash = payload.get("candidate_hash")
                if isinstance(candidate_hash, str):
                    seen.add(candidate_hash)
        return seen

    def _acquire_lock(self) -> None:
        try:
            self._lock_fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            if self._remove_stale_lock():
                self._lock_fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._lock_fd, f"pid={os.getpid()} ts={_utc_now()}\n".encode())
                return
            raise RuntimeError(f"DSS output is already locked: {self.lock_path}") from exc
        os.write(self._lock_fd, f"pid={os.getpid()} ts={_utc_now()}\n".encode())

    def _release_lock(self) -> None:
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None
        with suppress(FileNotFoundError):
            self.lock_path.unlink()

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, object]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")

    def _remove_stale_lock(self) -> bool:
        try:
            content = self.lock_path.read_text(encoding="utf-8")
        except OSError:
            return False
        pid = _parse_lock_pid(content)
        if pid is None or _pid_exists(pid):
            return False
        with suppress(FileNotFoundError):
            self.lock_path.unlink()
        return True


def should_use_random_injection(generated: int) -> bool:
    """Default shared random-unseen injection cadence for adaptive backends."""

    return generated > 0 and generated % 5 == 0


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _parse_lock_pid(content: str) -> int | None:
    for part in content.split():
        if not part.startswith("pid="):
            continue
        try:
            return int(part.removeprefix("pid="))
        except ValueError:
            return None
    return None


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
