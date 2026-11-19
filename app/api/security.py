"""The API key check. Part of Layer 1 (the front door)."""
import hmac

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings

# This tells FastAPI which header carries the key (it also gives the /docs page its Authorize button).
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    key: str | None = Depends(api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    # compare_digest takes the same time however many characters match, so the key can't be guessed by timing.
    if key is None or not hmac.compare_digest(key.encode(), settings.api_key.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
