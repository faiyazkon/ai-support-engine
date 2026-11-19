"""The pipeline: the belt that runs each layer in order. Later layers are added here.

Right now: Layer 2 (secret user ID), Layer 3 (limits), Layer 4 (cleaning), Layer 5 (hide private details)
and the database record.
A layer that says "stop" ends the trip with a fixed reply, and nothing after it runs.
Every message is written to the database when it arrives and updated when it ends.
"""
import time

from app.database import storage
from app.layers.cleaning import clean
from app.layers.identity import make_user_key
from app.layers.limits import get_limiter
from app.layers.privacy import hide_private
from app.layers.replies import fixed_reply
from app.api.schemas import IncomingMessage, Reply


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

    cleaned = clean(msg.text)  # Layer 4
    if cleaned.text == "":  # the message was only invisible characters
        reply = fixed_reply("empty", limiter.max_chars)
        storage.finish_message(message_id, reply.status, reason="empty", reply_text=reply.reply, latency_ms=_ms(started))
        return reply

    # The profile name is cleaned the same way as the message, so both are written the same way when compared.
    profile_name = None
    if msg.profile_name is not None:
        profile_name = clean(msg.profile_name).text

    hidden = hide_private(cleaned.text, profile_name)  # Layer 5

    reply = Reply(
        status="answered",
        reply=f"[layers 1-5 + database only] received a {len(cleaned.text)}-character message from {msg.channel}. "
              f"Hid {hidden.count} private details.",
    )
    storage.finish_message(message_id, reply.status, reply_text=reply.reply, text_sent_to_llm=hidden.text,
                           latency_ms=_ms(started))
    return reply
