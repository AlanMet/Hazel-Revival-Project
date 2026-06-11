"""Run bleak asyncio coroutines off the Tk main thread."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from typing import Any


class AsyncWorker:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def submit(
        self,
        coro,
        *,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> None:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        def _done(fut) -> None:
            try:
                result = fut.result()
            except BaseException as exc:
                if on_error:
                    on_error(exc)
                return
            if on_success:
                on_success(result)

        future.add_done_callback(_done)

    def shutdown(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=2)
