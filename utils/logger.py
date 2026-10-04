"""
utils/logger.py
---------------
Centralized logging configuration for the Expo Scraper project.

Provides:
    get_logger(name) -> loguru.Logger

Features:
    - Colored console output (dev-friendly)
    - Rotating log files under logs/ (size-based rotation + retention)
    - Separate error log
    - Suppresses noisy 3rd-party loggers (urllib3, selenium, etc.)

Usage:
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Scraping %s", url)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from loguru import logger as _logger

from config.settings import (
    LOG_DIR,
    LOG_FORMAT,
    LOG_LEVEL,
    LOG_RETENTION,
    LOG_ROTATION,
)

# ---------------------------------------------------------------------------
# Log file paths
# ---------------------------------------------------------------------------
APP_LOG_FILE = LOG_DIR / "app_{time:YYYY-MM-DD}.log"
ERROR_LOG_FILE = LOG_DIR / "error_{time:YYYY-MM-DD}.log"

# ---------------------------------------------------------------------------
# One-time configuration guard
# ---------------------------------------------------------------------------
_CONFIGURED: bool = False


def _configure() -> None:
    """Configure loguru sinks exactly once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    # Remove loguru's default stderr sink so we control formatting
    _logger.remove()

    # --- Console sink (colored, terse for dev) ---
    _logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        colorize=True,
        backtrace=True,
        diagnose=False,          # do not leak locals in tracebacks
        enqueue=False,           # keep synchronous for simplicity
    )

    # --- File sink (all levels) ---
    _logger.add(
        APP_LOG_FILE,
        level=LOG_LEVEL,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        compression="zip",
        encoding="utf-8",
        enqueue=True,            # safe for multi-threaded scrapers
        backtrace=True,
        diagnose=False,
    )

    # --- File sink (errors only) ---
    _logger.add(
        ERROR_LOG_FILE,
        level="ERROR",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}\n{exception}"
        ),
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    # --- Quiet down chatty 3rd-party libraries ---
    for noisy in (
        "urllib3",
        "requests",
        "selenium",
        "websockets",
        "httpx",
        "httpcore",
        "asyncio",
        "PIL",
    ):
        _logger.disable(noisy)

    _CONFIGURED = True


def get_logger(name: Optional[str] = None):
    """
    Return a configured loguru logger.

    Parameters
    ----------
    name : str, optional
        Usually `__name__` of the calling module. Attached via `.bind()`
        so it shows up in log records.

    Returns
    -------
    loguru.Logger
    """
    _configure()
    if name:
        return _logger.bind(module=name)
    return _logger


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    log = get_logger(__name__)
    log.debug("debug message (hidden if LOG_LEVEL=INFO)")
    log.info("info message")
    log.warning("warning message")
    log.error("error message")
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("caught an exception (full traceback)")
    log.success("done")

    print(f"\nLogs written to: {LOG_DIR}")
    print(f"App log   : {APP_LOG_FILE}")
    print(f"Error log : {ERROR_LOG_FILE}")