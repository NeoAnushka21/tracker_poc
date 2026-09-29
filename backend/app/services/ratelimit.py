"""Small in-memory sliding-window limits for sign-in (one server process, so memory is enough;
a restart clears them). Stops password guessing and sign-up floods."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app import config

_hits: dict[str, deque[float]] = defaultdict(deque)


def _recent(key: str, window_s: float) -> deque[float]:
    q = _hits[key]
    cutoff = time.monotonic() - window_s
    while q and q[0] < cutoff:
        q.popleft()
    return q


def _too_many(wait_s: float) -> HTTPException:
    minutes = max(1, round(wait_s / 60))
    return HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                         f"Too many attempts. Please wait about {minutes} minute{'s' if minutes > 1 else ''} and try again.")


def client_ip(request: Request) -> str:
    """The browser's address. Behind Render's proxy it's the first X-Forwarded-For entry. A client
    can fake that header, but only to dodge its own limit; it can't use it to block anyone else."""
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def check_ip(request: Request) -> None:
    """Every login / register / Google request counts against the caller's address."""
    q = _recent(f"ip:{client_ip(request)}", config.AUTH_REQUEST_WINDOW_S)
    if len(q) >= config.AUTH_REQUESTS_PER_IP:
        raise _too_many(q[0] + config.AUTH_REQUEST_WINDOW_S - time.monotonic())
    q.append(time.monotonic())


def check_reset_requests(email: str) -> None:
    """At most a few reset emails per address per hour, so nobody can flood someone's inbox."""
    q = _recent(f"reset:{email}", config.PASSWORD_RESET_WINDOW_S)
    if len(q) >= config.PASSWORD_RESETS_PER_EMAIL:
        raise _too_many(q[0] + config.PASSWORD_RESET_WINDOW_S - time.monotonic())
    q.append(time.monotonic())


def check_login_failures(email: str) -> None:
    q = _recent(f"fail:{email}", config.LOGIN_FAILURE_WINDOW_S)
    if len(q) >= config.LOGIN_FAILURES_PER_EMAIL:
        raise _too_many(q[0] + config.LOGIN_FAILURE_WINDOW_S - time.monotonic())


def record_login_failure(email: str) -> None:
    _recent(f"fail:{email}", config.LOGIN_FAILURE_WINDOW_S).append(time.monotonic())


def clear_login_failures(email: str) -> None:
    _hits.pop(f"fail:{email}", None)


def reset() -> None:
    """Tests: start from a clean slate."""
    _hits.clear()
