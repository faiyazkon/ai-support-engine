"""Settings, read from environment variables or the .env file.

If API_KEY or ID_SECRET is missing or too short the app refuses to start, so you can never run
the bot by accident with the front door unlocked.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = Field(min_length=16)
    # Secret ink for the user IDs (Layer 2). Changing it changes every ID, so keep it safe and never change it.
    id_secret: str = Field(min_length=32)
    max_body_bytes: int = Field(default=10_000, gt=0)

    # Layer 3 limits. These numbers are starting points, not measured values; change them in .env.
    max_message_chars: int = Field(default=500, gt=0)
    rate_limit_per_minute: int = Field(default=5, gt=0)
    user_daily_limit: int = Field(default=50, gt=0)
    global_daily_limit: int = Field(default=2000, gt=0)

    # Storage. SQLite is a single file. To use PostgreSQL later, only this line changes,
    # for example postgresql+psycopg://user:password@localhost/support
    database_url: str = "sqlite:///data/support.db"
    # Message texts older than this are erased. The rest of the row (time, outcome, counts) stays.
    retention_days: int = Field(default=30, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
