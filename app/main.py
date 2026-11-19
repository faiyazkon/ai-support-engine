"""Where the program starts:  uvicorn app.main:app

This file only puts the pieces together. The real work lives in the folders:
  api/       the front door (addresses, key check, size check, message shapes)   Layer 1
  layers/    one file per layer on the belt (secret ID, limits, cleaning, ...)    Layers 2 and up
  database/  tables and the functions that read and write them
  core/      settings
  pipeline.py  the belt that runs the layers in order
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.middleware import BodySizeLimitMiddleware
from app.api.routes import router
from app.core.config import get_settings
from app.database.connection import init_db
from app.database.storage import purge_old_texts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs once when the server starts: make sure the tables exist, and erase old message texts
    init_db()
    purge_old_texts(get_settings().retention_days)
    yield


def create_app() -> FastAPI:
    settings = get_settings()  # raises at startup if API_KEY or ID_SECRET is missing
    app = FastAPI(title="AI Customer Support Engine", lifespan=lifespan)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.include_router(router)
    return app


app = create_app()
