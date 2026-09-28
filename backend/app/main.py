from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config, models  # noqa: F401  (models registers tables)
from app.data_migrations import run_all as run_data_migrations
from app.db import Base, SessionLocal, _is_sqlite, add_missing_columns, engine
from app.routers import actions, admin, auth, chat, dashboard, entries, foods, profile, water


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not _is_sqlite and config.SECRET_KEY == config.DEV_SECRET_KEY:
        # A shared database means a real deployment: sessions must not be signed with the
        # well-known development key.
        raise RuntimeError("Set SECRET_KEY in the environment before using a Postgres database.")
    # V1: create tables directly and add any new nullable columns. Switch to Alembic
    # before making changes this can't handle (renames, NOT NULL columns, type changes).
    Base.metadata.create_all(engine)
    add_missing_columns()
    with SessionLocal() as db:
        run_data_migrations(db)
    yield


app = FastAPI(title=config.APP_NAME, lifespan=lifespan)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(chat.router)
app.include_router(actions.router)
app.include_router(dashboard.router)
app.include_router(foods.router)
app.include_router(water.router)
app.include_router(admin.router)
app.include_router(entries.router)


@app.get("/api/health")
def health(response: Response):
    # Deliberately doesn't touch the database, so uptime pings don't keep Neon awake.
    # Readable from any origin: the always-on launcher page (another address) polls it while
    # the free server wakes. It carries no user data and needs no cookies.
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-store"
    return {"ok": True}


def mount_frontend(app: FastAPI, dist: Path) -> bool:
    """Serve the built React app from the backend: hashed assets as static files, any other
    non-API path gets index.html so the single-page app can handle it. Registered after the
    API routes, so they always win."""
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
        file = (dist / path).resolve()
        if path and file.is_file() and dist in file.parents:   # favicon.svg etc.; no ../ escapes
            return FileResponse(file)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return True


mount_frontend(app, config.FRONTEND_DIST)
