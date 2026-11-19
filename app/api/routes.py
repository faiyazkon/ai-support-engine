"""The addresses the outside world can call. Part of Layer 1 (the front door).

A message lands in the function `message` below. By the time it runs:
  1. the size was checked   (api/middleware.py)
  2. the API key was checked (api/security.py)
  3. the shape was checked   (api/schemas.py, by Pydantic)
Then it is handed to the belt (pipeline.py), and the Reply that comes back is sent to the sender.
"""
from fastapi import APIRouter, Depends

from app import pipeline
from app.api.schemas import IncomingMessage, Reply
from app.api.security import require_api_key

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/message", response_model=Reply, dependencies=[Depends(require_api_key)])
async def message(msg: IncomingMessage) -> Reply:
    return await pipeline.handle(msg)
