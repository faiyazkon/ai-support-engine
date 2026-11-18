"""The pipeline. Right now it is an empty placeholder.

Each later layer (user ID, limits, cleanup, redaction, attack checks, search, Gemini,
reply checks) will be added here one at a time. main.py only ever calls handle().
"""
from app.schemas import IncomingMessage, Reply


async def handle(msg: IncomingMessage) -> Reply:
    return Reply(
        status="answered",
        reply=f"[layer 1 only] received a {len(msg.text)}-character message from {msg.channel}.",
    )
