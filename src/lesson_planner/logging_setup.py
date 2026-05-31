from __future__ import annotations

from pathlib import Path
from typing import Optional
import logging
import sys

from .config import settings

logger = logging.getLogger(__name__)

_configured = False
_console_handler: Optional[logging.Handler] = None
_file_handler: Optional[logging.Handler] = None


def _build_formatter(environment: str, fmt_time: str = "%Y-%m-%d %H:%M:%S") -> logging.Formatter:
    if environment.upper() == "PRODUCTION":
        fmt = "ts=%(asctime)s level=%(levelname)s module=%(name)s msg=\"%(message)s\""
        return logging.Formatter(fmt, datefmt=fmt_time)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    return logging.Formatter(fmt, datefmt=fmt_time)


def configure_logging(log_level_override: Optional[str] = None) -> None:
    """Configure root logging for the application.

    Args:
        log_level_override: Optional uppercase log level to override settings.

    Returns:
        None
    """
    global _configured, _console_handler, _file_handler

    level_name = (log_level_override or settings.LOG_LEVEL).upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    formatter = _build_formatter(settings.ENVIRONMENT)

    if not _configured:
        _console_handler = logging.StreamHandler(sys.stdout)
        _console_handler.setLevel(level)
        _console_handler.setFormatter(formatter)
        root.addHandler(_console_handler)

        if settings.log_to_file:
            if not settings.LOG_FILE_PATH:
                logger.warning("LOG_FILE_PATH is not set; skipping file logger")
            else:
                try:
                    parent = Path(settings.LOG_FILE_PATH).parent
                    parent.mkdir(parents=True, exist_ok=True)
                    _file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
                    _file_handler.setLevel(level)
                    _file_handler.setFormatter(formatter)
                    root.addHandler(_file_handler)
                except (PermissionError, OSError) as exc:
                    logger.warning("Unable to create log file path: %s", exc)
        _configured = True
        return

    if _console_handler is not None:
        _console_handler.setLevel(level)
        _console_handler.setFormatter(formatter)
    if _file_handler is not None:
        _file_handler.setLevel(level)
        _file_handler.setFormatter(formatter)
