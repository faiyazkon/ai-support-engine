"""The tables.

users     one row per person (by secret label, never the real chat ID): first/last seen, message count, strikes.
messages  one row per message: what happened to it, and the numbers we want to measure.

Times are stored as UTC. A message's text columns are erased after RETENTION_DAYS; the rest of the row stays.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    user_key: Mapped[str] = mapped_column(String(64), primary_key=True)  # the Layer 2 label
    channel: Mapped[str] = mapped_column(String(32))
    first_seen: Mapped[datetime] = mapped_column(DateTime)
    last_seen: Mapped[datetime] = mapped_column(DateTime)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    strike_count: Mapped[int] = mapped_column(Integer, default=0)  # used from Layer 6 on
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_key: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_key"))
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    # True only if the message passed Layer 3. Daily limits count these rows.
    counted: Mapped[bool] = mapped_column(Boolean, default=False)
    # in_progress, answered, refused, needs_human or error
    status: Mapped[str] = mapped_column(String(16), default="in_progress")
    reason: Mapped[str | None] = mapped_column(String(32), nullable=True)      # why it was stopped
    category: Mapped[str | None] = mapped_column(String(16), nullable=True)    # lead, spam, support_issue, non_lead

    # These text columns are erased after RETENTION_DAYS.
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)     # only kept for messages that passed Layer 3
    text_sent_to_llm: Mapped[str | None] = mapped_column(Text, nullable=True)  # exactly what Gemini received (Layer 8)
    reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    cited_sources: Mapped[str | None] = mapped_column(Text, nullable=True)     # JSON list of chunk ids
    flags: Mapped[str | None] = mapped_column(Text, nullable=True)             # JSON list, e.g. weak attack flags
    llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (Index("ix_messages_user_time", "user_key", "created_at"),)
