"""Desktop entry point — PyQt6 + qasync."""

from __future__ import annotations

import asyncio
import sys

from PyQt6.QtWidgets import QApplication
from qasync import QEventLoop

from hazel_revive.app import HazelReviveApp
from hazel_revive.log import get_logger


def _task_exception_handler(loop, context) -> None:
    log = get_logger()
    exc = context.get("exception")
    if exc is not None:
        log.error("Unhandled async error: %s", exc, exc_info=exc)
    else:
        log.error("Unhandled async error: %s", context.get("message", context))


def main() -> None:
    log = get_logger()
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    loop.set_exception_handler(_task_exception_handler)

    window = HazelReviveApp()
    window.show()
    log.info("Window shown")

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
