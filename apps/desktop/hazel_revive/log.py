"""Logging to file, stderr, and optional Qt log panel."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

_APP_DIR = Path(__file__).resolve().parent.parent
_FALLBACK_LOG_DIR = _APP_DIR / "logs"
_HOME_LOG_DIR = Path.home() / ".local" / "state" / "hazel-revive"


def _log_dir() -> Path:
    try:
        _HOME_LOG_DIR.mkdir(parents=True, exist_ok=True)
        return _HOME_LOG_DIR
    except OSError:
        _FALLBACK_LOG_DIR.mkdir(parents=True, exist_ok=True)
        return _FALLBACK_LOG_DIR


def log_file_path() -> Path:
    return _log_dir() / "desktop.log"

_log: logging.Logger | None = None


class _QtLogEmitter(QObject):
    message = pyqtSignal(str)


_emitter = _QtLogEmitter()


class QtLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            _emitter.message.emit(self.format(record))
        except Exception:
            self.handleError(record)


def get_logger() -> logging.Logger:
    global _log
    if _log is not None:
        return _log

    log_dir = _log_dir()
    logger = logging.getLogger("hazel_revive")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    log_file = log_dir / "desktop.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.addHandler(QtLogHandler())
    logger.propagate = False
    _log = logger
    return logger


def connect_log_panel(append_fn) -> None:
    _emitter.message.connect(append_fn)
