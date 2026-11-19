"""LAYER 3: limits.

Checks, in this order, and stops at the first one that fails:
  1. rate      too many messages from this person in the last 60 seconds (kept in memory)
  2. too_long  message longer than MAX_MESSAGE_CHARS
  3. user_daily    this person already used their messages for today (counted in the database)
  4. global_daily  the whole shop already used its messages for today (your cost safety net)

The daily numbers are counted from the messages table, so they survive a restart.
Only messages that passed this layer are counted. The "day" is the Dhaka day.
The rate check lives in memory on purpose: it only looks back 60 seconds, so a restart costs nothing.
"""
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from app.core.config import get_settings
from app.database import storage

DHAKA = timezone(timedelta(hours=6))  # the shop's "day" runs on Dhaka time (no daylight saving there)
RATE_WINDOW_SECONDS = 60


def dhaka_day_start_utc(now: float) -> datetime:
    """Midnight at the start of today in Dhaka, as a naive UTC time (the form the database stores)."""
    local = datetime.fromtimestamp(now, DHAKA).replace(hour=0, minute=0, second=0, microsecond=0)
    return local.astimezone(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class LimitResult:
    allowed: bool
    reason: str | None = None  # "rate", "too_long", "user_daily" or "global_daily"


class Limiter:
    def __init__(self, max_chars, per_minute, per_user_day, global_day, daily_counts, clock=time.time):
        self.max_chars = max_chars
        self.per_minute = per_minute
        self.per_user_day = per_user_day
        self.global_day = global_day
        self._daily_counts = daily_counts  # function (user_key, since) -> (user's count, shop's count)
        self._clock = clock  # a fake clock can be passed in, so tests don't have to wait
        self._recent: dict[str, deque] = {}

    def _forget_idle_users(self, now: float) -> None:
        if len(self._recent) > 5000:  # keep memory from growing forever
            self._recent = {k: v for k, v in self._recent.items() if v and v[-1] > now - RATE_WINDOW_SECONDS}

    def check(self, user_key: str, text: str) -> LimitResult:
        now = self._clock()
        self._forget_idle_users(now)

        # 1. rate (every attempt is recorded)
        window = self._recent.setdefault(user_key, deque())
        while window and window[0] <= now - RATE_WINDOW_SECONDS:
            window.popleft()
        window.append(now)
        if len(window) > self.per_minute:
            return LimitResult(False, "rate")

        # 2. length
        if len(text) > self.max_chars:
            return LimitResult(False, "too_long")

        # 3 and 4. daily numbers, from the database
        user_count, shop_count = self._daily_counts(user_key, dhaka_day_start_utc(now))
        if user_count >= self.per_user_day:
            return LimitResult(False, "user_daily")
        if shop_count >= self.global_day:
            return LimitResult(False, "global_daily")

        return LimitResult(True)


@lru_cache
def get_limiter() -> Limiter:
    s = get_settings()
    return Limiter(s.max_message_chars, s.rate_limit_per_minute, s.user_daily_limit, s.global_daily_limit,
                   daily_counts=storage.count_counted)
