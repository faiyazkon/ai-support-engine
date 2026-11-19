"""The shapes of what comes in and what goes out. Pydantic enforces them."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncomingMessage(BaseModel):
    # Unknown fields are rejected, so a typo like "tekst" shows up as an error instead of being ignored.
    model_config = ConfigDict(extra="forbid")

    channel: Literal["telegram", "web", "test"]
    user_id: str = Field(min_length=1, max_length=64)
    profile_name: str | None = Field(default=None, max_length=100)
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank")
        return v  # left untouched here; cleaning happens in a later layer


class Reply(BaseModel):
    status: Literal["answered", "refused", "needs_human", "error"]
    reply: str
