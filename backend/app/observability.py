"""Logs with request ids, a friendly 500 with a reference, and optional Sentry error reports.

Every response carries X-Request-ID. An unexpected error is logged with that id and the user sees
"Something went wrong (ref …)", so a reported ref leads straight to the log line (Render → Logs).
Sentry is used only when SENTRY_DSN is set, and sends no chat text, request bodies, cookies or IPs.
"""
import contextvars
import logging
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import config

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
log = logging.getLogger("tandurust")


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


def setup_logging() -> None:
    """App loggers (tandurust.*, macbro.*) at INFO, one line each, with the request id."""
    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"))
    for name in ("tandurust", "macbro"):
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False


def setup_sentry() -> bool:
    if not config.SENTRY_DSN:
        return False
    import sentry_sdk
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        environment=config.SENTRY_ENVIRONMENT,
        send_default_pii=False,          # no cookies, IP addresses or user details
        max_request_body_size="never",   # never the request body (chat messages, food, passwords)
        include_local_variables=False,   # stack frames without their variables (could hold user data)
        traces_sample_rate=0,            # errors only; performance tracing would use the free quota
    )
    return True


def install(app: FastAPI) -> None:
    """Request ids, and a friendly 500 for unexpected errors. The error is caught here, inside the
    other middleware, so the reply still gets the security headers and the log line keeps its id."""
    @app.middleware("http")
    async def request_id_and_errors(request: Request, call_next):
        rid = secrets.token_hex(4)
        token = request_id.set(rid)
        try:
            response = await call_next(request)
        except Exception:
            log.exception("Unhandled error on %s %s", request.method, request.url.path)
            if config.SENTRY_DSN:
                import sentry_sdk
                sentry_sdk.capture_exception()
            response = JSONResponse(
                status_code=500,
                content={"detail": f"Something went wrong on our side (ref {rid}). Please try again."})
        finally:
            request_id.reset(token)
        response.headers["X-Request-ID"] = rid
        return response
