"""The pipeline: the belt that runs each layer in order. Later layers are added here.

Right now: Layer 2 (secret user ID), Layer 3 (limits) and the database record of what happened.
A layer that says "stop" ends the trip with a fixed reply, and nothing after it runs.
Every message is written to the database when it arrives and updated when it ends.
"""
import time

from app import storage
from app.identity import make_user_key
from app.limits import get_limiter
from app.replies import fixed_reply
from app.schemas import IncomingMessage, Reply


def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


async def handle(msg: IncomingMessage) -> Reply:
    started = time.perf_counter()
    user_key = make_user_key(msg.channel, msg.user_id)  # Layer 2

    limiter = get_limiter()
    result = limiter.check(user_key, msg.text)  # Layer 3
    message_id = storage.begin_message(user_key, msg.channel, msg.text, counted=result.allowed)
    if not result.allowed:
        reply = fixed_reply(result.reason, limiter.max_chars)
        storage.finish_message(message_id, reply.status, reason=result.reason, reply_text=reply.reply,
                               latency_ms=_ms(started))
        return reply

    reply = Reply(
        status="answered",
        reply=f"[layers 1-3 + database only] received a {len(msg.text)}-character message from {msg.channel}.",
    )
    storage.finish_message(message_id, reply.status, reply_text=reply.reply, latency_ms=_ms(started))
    return reply
