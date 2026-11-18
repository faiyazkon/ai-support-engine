"""The pipeline: the belt that runs each layer in order. Later layers are added here.

Right now: Layer 2 (secret user ID) and Layer 3 (limits). Everything after them is still missing.
A layer that says "stop" ends the trip with a fixed reply, and nothing after it runs.
"""
from app.identity import make_user_key
from app.limits import get_limiter
from app.replies import fixed_reply
from app.schemas import IncomingMessage, Reply


async def handle(msg: IncomingMessage) -> Reply:
    user_key = make_user_key(msg.channel, msg.user_id)  # Layer 2

    limiter = get_limiter()
    result = limiter.check(user_key, msg.text)  # Layer 3
    if not result.allowed:
        return fixed_reply(result.reason, limiter.max_chars)

    return Reply(
        status="answered",
        reply=f"[layers 1-3 only] received a {len(msg.text)}-character message from {msg.channel}.",
    )