"""Everything the program reads from or writes to the database goes through these functions."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update

from app.db import get_session_factory
from app.models import Message, User


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # stored as naive UTC everywhere


def begin_message(user_key: str, channel: str, text: str, counted: bool) -> int:
    """Record that a message arrived. Creates the user the first time we see them. Returns the message id."""
    now = utcnow()
    with get_session_factory()() as session, session.begin():
        user = session.get(User, user_key)
        if user is None:
            user = User(user_key=user_key, channel=channel, first_seen=now, last_seen=now, message_count=0, strike_count=0)
            session.add(user)
            session.flush()  # the user row must exist before a message row points at it
        user.last_seen = now
        user.message_count += 1
        message = Message(
            user_key=user_key,
            created_at=now,
            counted=counted,
            status="in_progress",
            # Refused messages were never answered, so we don't keep their text (saves space and privacy).
            original_text=text if counted else None,
        )
        session.add(message)
        session.flush()
        return message.id


def finish_message(message_id: int, status: str, *, reason=None, reply_text=None, category=None, cited_sources=None,
                   flags=None, llm_calls=0, tokens_in=0, tokens_out=0, latency_ms=None, text_sent_to_llm=None) -> None:
    with get_session_factory()() as session, session.begin():
        session.execute(
            update(Message).where(Message.id == message_id).values(
                status=status, reason=reason, reply_text=reply_text, category=category, cited_sources=cited_sources,
                flags=flags, llm_calls=llm_calls, tokens_in=tokens_in, tokens_out=tokens_out,
                latency_ms=latency_ms, text_sent_to_llm=text_sent_to_llm,
            )
        )


def count_counted(user_key: str, since: datetime) -> tuple[int, int]:
    """(this person's, whole shop's) number of messages that passed Layer 3 since `since` (UTC)."""
    with get_session_factory()() as session:
        mine = session.scalar(select(func.count()).select_from(Message).where(
            Message.user_key == user_key, Message.counted.is_(True), Message.created_at >= since))
        everyone = session.scalar(select(func.count()).select_from(Message).where(
            Message.counted.is_(True), Message.created_at >= since))
        return mine or 0, everyone or 0


def purge_old_texts(days: int, now: datetime | None = None) -> int:
    """Erase the text columns of messages older than `days`. Keeps time, outcome and counts. Returns how many rows changed."""
    cutoff = (now or utcnow()) - timedelta(days=days)
    with get_session_factory()() as session, session.begin():
        result = session.execute(
            update(Message)
            .where(Message.created_at < cutoff)
            .where((Message.original_text.is_not(None)) | (Message.text_sent_to_llm.is_not(None)) | (Message.reply_text.is_not(None)))
            .values(original_text=None, text_sent_to_llm=None, reply_text=None)
        )
        return result.rowcount
