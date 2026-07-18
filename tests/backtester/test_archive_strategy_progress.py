from __future__ import annotations

import json
from pathlib import Path


def test_archived_long_running_strategies_keep_progress_enabled() -> None:
    archive_dir = Path("strategies/archive")
    archived_configs = sorted(archive_dir.glob("*.json"))

    offenders: list[str] = []
    for path in archived_configs:
        raw = json.loads(path.read_text())
        params = raw.get("params", {})
        if params.get("progress") is False:
            offenders.append(str(path))

    assert offenders == []
