"""LAYER 1: the front door.

Every message from outside lands here, in the function `message` below.
Order of checks:
  1. body size            (BodySizeLimitMiddleware, before anything is read)
  2. API key              (require_api_key)
  3. shape of the JSON    (IncomingMessage, checked by Pydantic)
Then the clean message goes to pipeline.handle(), and its Reply is sent back.
"""
import hmac
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import APIKeyHeader

from app import pipeline
from app.config import Settings, get_settings
from app.db import init_db
from app.middleware import BodySizeLimitMiddleware
from app.schemas import IncomingMessage, Reply
from app.storage import purge_old_texts

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    key: str | None = Depends(api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    # compare_digest takes the same time however many characters match, so the key can't be guessed by timing.
    if key is None or not hmac.compare_digest(key.encode(), settings.api_key.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs once when the server starts: make sure the tables exist, and erase old message texts
    init_db()
    purge_old_texts(get_settings().retention_days)
    yield


def create_app() -> FastAPI:
    settings = get_settings()  # raises at startup if API_KEY is missing
    app = FastAPI(title="AI Customer Support Engine", lifespan=lifespan)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.post("/message", response_model=Reply, dependencies=[Depends(require_api_key)])
    async def message(msg: IncomingMessage) -> Reply:
        return await pipeline.handle(msg)

    return app


app = create_app()
