"""Settings, read from environment variables or the .env file.

If API_KEY is missing or too short the app refuses to start, so you can never run
the bot by accident with the front door unlocked.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = Field(min_length=16)
    max_body_bytes: int = Field(default=10_000, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
