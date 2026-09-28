from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (registers tables)
from app.db import Base, add_missing_columns, engine
from app.routers import actions, auth, chat, dashboard, foods, profile


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # V1: create tables directly and add any new nullable columns. Switch to Alembic
    # before making changes this can't handle (renames, NOT NULL columns, type changes).
    Base.metadata.create_all(engine)
    add_missing_columns()
    yield


app = FastAPI(title="Macro Tracker", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(chat.router)
app.include_router(actions.router)
app.include_router(dashboard.router)
app.include_router(foods.router)


@app.get("/api/health")
def health():
    return {"ok": True}
