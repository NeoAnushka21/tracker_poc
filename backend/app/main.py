from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (registers tables)
from app.db import Base, engine
from app.routers import actions, auth, chat, dashboard, foods, profile


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # V1: create tables directly. Switch to Alembic migrations before the schema
    # needs to change on a database with real data in it.
    Base.metadata.create_all(engine)
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
