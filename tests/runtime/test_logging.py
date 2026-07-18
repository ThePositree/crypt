from __future__ import annotations

import logging
from pathlib import Path

import pytest
from loguru import logger

from crypt.runtime.logging import configure_runtime_logging


def test_runtime_logging_routes_info_to_stdout_and_warning_to_stderr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    try:
        configure_runtime_logging("INFO", tmp_path)

        logger.debug("hidden debug")
        logger.info("visible info")
        logger.warning("visible warning")
        logging.getLogger("stdlib-test").info("stdlib info")

        captured = capsys.readouterr()
        assert "hidden debug" not in captured.out
        assert "hidden debug" not in captured.err
        assert "visible info" in captured.out
        assert "stdlib info" in captured.out
        assert "visible warning" in captured.err
        assert "visible info" not in captured.err
    finally:
        logger.remove()
