from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config, models, observability  # noqa: F401  (models registers tables)
from app.data_migrations import run_all as run_data_migrations
from app.db import SessionLocal, _is_sqlite, engine
from app.migrate import migrate
from app.routers import actions, admin, auth, chat, dashboard, entries, foods, profile, waitlist, water


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not _is_sqlite and config.SECRET_KEY == config.DEV_SECRET_KEY:
        # A shared database means a real deployment: sessions must not be signed with the
        # well-known development key.
        raise RuntimeError("Set SECRET_KEY in the environment before using a Postgres database.")
    migrate(engine)   # Alembic: see app/migrate.py
    with SessionLocal() as db:
        run_data_migrations(db)
    yield


observability.setup_logging()
observability.setup_sentry()

_docs = {} if config.API_DOCS else {"docs_url": None, "redoc_url": None, "openapi_url": None}
app = FastAPI(title=config.APP_NAME, lifespan=lifespan, **_docs)

# Browser security headers on every response (OWASP secure headers). The CSP allows only our own
# files plus Google's sign-in button (the origins Google documents for Sign in with Google); inline
# scripts are not allowed. React's style attributes need 'unsafe-inline' for styles only.
# 'wasm-unsafe-eval' lets the pack scanner run its WebAssembly (our own files, src/scan.ts); it
# allows compiling WebAssembly only, not eval() of JavaScript.
_GSI = "https://accounts.google.com/gsi/"
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    f"script-src 'self' 'wasm-unsafe-eval' {_GSI}client",
    f"style-src 'self' 'unsafe-inline' {_GSI}style",
    f"frame-src {_GSI}",
    f"connect-src 'self' {_GSI}",
    "img-src 'self' data:",
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])
SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # The mic (voice input) and the camera (scanning a pack) are used on our own pages only.
    "Permissions-Policy": "microphone=(self), camera=(self), geolocation=(), payment=(), usb=()",
    # Google's sign-in popup needs to talk back to this page.
    "Cross-Origin-Opener-Policy": "same-origin-allow-popups",
}


observability.install(app)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if config.COOKIE_SECURE:   # only over HTTPS: browsers then refuse plain HTTP for a year
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response


@app.middleware("http")
async def waitlist_cors(request: Request, call_next):
    """The always-on welcome site (LAUNCHER_ORIGIN, another address) sends the "Join the community"
    form here. Only /api/waitlist is opened to it, without cookies; every other route stays same-origin."""
    origin = request.headers.get("origin", "")
    allowed = (config.LAUNCHER_ORIGIN and origin == config.LAUNCHER_ORIGIN
               and request.url.path.startswith("/api/waitlist"))
    if allowed and request.method == "OPTIONS":
        return Response(status_code=204, headers={
            "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "GET, POST",
            "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "600", "Vary": "Origin"})
    response = await call_next(request)
    if allowed:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    return response


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(chat.router)
app.include_router(actions.router)
app.include_router(dashboard.router)
app.include_router(foods.router)
app.include_router(water.router)
app.include_router(admin.router)
app.include_router(entries.router)
app.include_router(waitlist.router)


# GET and HEAD: uptime monitors (e.g. UptimeRobot's free plan) ping with HEAD, and a 405 would
# show the site as down. The pings also keep the free Render service from sleeping.
@app.api_route("/api/health", methods=["GET", "HEAD"])
def health(response: Response):
    # Deliberately doesn't touch the database, so uptime pings don't keep Neon awake.
    # Readable from any origin: the always-on launcher page (another address) polls it while
    # the free server wakes. It carries no user data and needs no cookies.
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-store"
    return {"ok": True}


def mount_frontend(app: FastAPI, dist: Path) -> bool:
    """Serve the built React app from the backend: hashed assets as static files, /welcome is the
    welcome page (welcome.html, where signed-out visitors land), any other non-API path gets
    index.html so the single-page app can handle it. Registered after the API routes, so they
    always win."""
    dist = dist.resolve()
    index = dist / "index.html"
    if not index.is_file():
        return False
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        if path.rstrip("/") == "welcome" and (dist / "welcome.html").is_file():
            return FileResponse(dist / "welcome.html", headers={"Cache-Control": "no-cache"})
        # Privacy and Terms are pre-rendered at build time (vite.config.ts), so their text is in the HTML
        # for readers that don't run JavaScript (Google's brand check); the app then takes over as usual.
        page = path.rstrip("/")
        if page in ("privacy", "terms") and (dist / f"{page}.html").is_file():
            return FileResponse(dist / f"{page}.html", headers={"Cache-Control": "no-cache"})
        file = (dist / path).resolve()
        if path and file.is_file() and dist in file.parents:   # favicon.svg etc.; no ../ escapes
            return FileResponse(file)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return True


mount_frontend(app, config.FRONTEND_DIST)
