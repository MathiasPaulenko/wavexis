"""Resource cleanup for orphaned browser processes.

Registers atexit and signal handlers to ensure browser backends are closed
even when the process crashes or is interrupted.
"""

from __future__ import annotations

import atexit
import contextlib
import logging
import signal
import sys
import threading
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["register_backend", "unregister_backend"]

_registered_backends: list[Any] = []
_cleanup_done = False

_SIGNAL_NAMES: dict[int, str] = {
    signal.SIGINT: "SIGINT",
    signal.SIGTERM: "SIGTERM",
}

_sigbreak = getattr(signal, "SIGBREAK", None)
if _sigbreak is not None:
    _SIGNAL_NAMES[_sigbreak] = "SIGBREAK"


def register_backend(backend: Any) -> None:
    """Register a backend for cleanup on exit.

    Args:
        backend: A backend instance with an async ``close()`` method.
    """
    _registered_backends.append(backend)


def unregister_backend(backend: Any) -> None:
    """Unregister a backend after it has been closed normally.

    Args:
        backend: The backend instance to remove from cleanup tracking.
    """
    if backend in _registered_backends:
        _registered_backends.remove(backend)


def _cleanup_sync() -> None:
    """Synchronously attempt to close all registered backends.

    Uses ``asyncio.run`` if there are backends to close.
    """
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True

    if not _registered_backends:
        return

    import asyncio

    async def _close_all() -> None:
        for backend in list(_registered_backends):
            with contextlib.suppress(Exception):
                await backend.close()

    try:
        loop = asyncio.get_running_loop()
        if hasattr(loop, "_thread_id") and loop._thread_id == threading.current_thread().ident:
            asyncio.ensure_future(_close_all())
        else:
            future = asyncio.run_coroutine_threadsafe(_close_all(), loop)
            future.result(timeout=5)
    except TimeoutError:
        pass
    except RuntimeError:
        # No running loop, use asyncio.run()
        with contextlib.suppress(Exception):
            asyncio.run(_close_all())

    _registered_backends.clear()


def _signal_handler(signum: int, frame: Any) -> None:
    """Handle signals by cleaning up and re-raising.

    Args:
        signum: Signal number received.
        frame: Current stack frame.
    """
    _cleanup_sync()
    name = _SIGNAL_NAMES.get(signum, str(signum))
    sys.stderr.write(f"\nwavexis: received {name}, cleaning up…\n")
    sys.exit(128 + signum)


def _setup_signal_handlers() -> None:
    """Register signal handlers for cleanup."""
    for sig in _SIGNAL_NAMES:
        with contextlib.suppress(OSError, ValueError):
            signal.signal(sig, _signal_handler)


atexit.register(_cleanup_sync)
_setup_signal_handlers()
