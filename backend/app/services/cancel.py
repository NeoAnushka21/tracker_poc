"""Cancelling an in-flight chat turn (the Stop button).

The browser aborts its request and also calls /api/chat/cancel, because the server would
otherwise finish the turn and save a proposal the user no longer wants. A turn checks for
cancellation after each LLM call, and `finish_or_cancelled` is the single atomic point
before commit: after it, a cancel reports "finished" and the UI shows the saved reply.

In-memory, so it assumes one server process (true for this app's deployment).
"""
import threading
import time

_TTL_SECONDS = 600
_lock = threading.Lock()
_state: dict[tuple[int, str], tuple[str, float]] = {}   # (user_id, request_id) -> (status, ts)


class ChatCancelled(Exception):
    pass


def _prune(now: float) -> None:
    for key in [k for k, (_, ts) in _state.items() if now - ts > _TTL_SECONDS]:
        del _state[key]


def start(user_id: int, request_id: str | None) -> None:
    if not request_id:
        return
    with _lock:
        now = time.time()
        _prune(now)
        # A cancel can arrive before the request itself; keep it.
        if _state.get((user_id, request_id), ("", 0))[0] != "cancelled":
            _state[(user_id, request_id)] = ("running", now)


def raise_if_cancelled(user_id: int, request_id: str | None) -> None:
    if request_id and _state.get((user_id, request_id), ("", 0))[0] == "cancelled":
        raise ChatCancelled()


def finish_or_cancelled(user_id: int, request_id: str | None) -> None:
    """Atomically: raise if cancelled, else mark finished (later cancels are too late)."""
    if not request_id:
        return
    with _lock:
        if _state.get((user_id, request_id), ("", 0))[0] == "cancelled":
            raise ChatCancelled()
        _state[(user_id, request_id)] = ("finished", time.time())


def cancel(user_id: int, request_id: str) -> str:
    """Returns 'cancelled', or 'finished' if the turn was already saved."""
    with _lock:
        status, _ = _state.get((user_id, request_id), ("", 0))
        if status == "finished":
            return "finished"
        _state[(user_id, request_id)] = ("cancelled", time.time())
        return "cancelled"
