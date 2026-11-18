"""LAYER 3: limits.

Checks, in this order, and stops at the first one that fails:
  1. rate      too many messages from this person in the last 60 seconds
  2. too_long  message longer than MAX_MESSAGE_CHARS
  3. user_daily  this person already used their messages for today
  4. global_daily  the whole shop already used its messages for today (your cost safety net)

Only messages that pass all four are counted toward the daily numbers.
Every attempt counts toward the rate check, so someone who keeps hammering stays blocked.

Honest limit: the counters live in this program's memory. They reset when the server restarts,
and two server processes would not share them. A database replaces this later.
"""
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from app.config import get_settings

DHAKA = timezone(timedelta(hours=6))  # the shop's "day" runs on Dhaka time (no daylight saving there)
RATE_WINDOW_SECONDS = 60


@dataclass(frozen=True)
class LimitResult:
    allowed: bool
    reason: str | None = None  # "rate", "too_long", "user_daily" or "global_daily"


class Limiter:
    def __init__(self, max_chars, per_minute, per_user_day, global_day, clock=time.time):
        self.max_chars = max_chars
        self.per_minute = per_minute
        self.per_user_day = per_user_day
        self.global_day = global_day
        self._clock = clock  # a fake clock can be passed in, so tests don't have to wait
        self._recent: dict[str, deque] = {}
        self._day = ""
        self._user_counts: dict[str, int] = {}
        self._global_count = 0

    def _roll_day(self, now: float) -> None:
        today = datetime.fromtimestamp(now, DHAKA).date().isoformat()
        if today != self._day:  # a new Dhaka day: all daily counters start again
            self._day = today
            self._user_counts = {}
            self._global_count = 0

    def _forget_idle_users(self, now: float) -> None:
        if len(self._recent) > 5000:  # keep memory from growing forever
            self._recent = {k: v for k, v in self._recent.items() if v and v[-1] > now - RATE_WINDOW_SECONDS}

    def check(self, user_key: str, text: str) -> LimitResult:
        now = self._clock()
        self._roll_day(now)
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

        # 3 and 4. daily numbers
        if self._user_counts.get(user_key, 0) >= self.per_user_day:
            return LimitResult(False, "user_daily")
        if self._global_count >= self.global_day:
            return LimitResult(False, "global_daily")

        # passed everything: count it
        self._user_counts[user_key] = self._user_counts.get(user_key, 0) + 1
        self._global_count += 1
        return LimitResult(True)


@lru_cache
def get_limiter() -> Limiter:
    s = get_settings()
    return Limiter(s.max_message_chars, s.rate_limit_per_minute, s.user_daily_limit, s.global_daily_limit)