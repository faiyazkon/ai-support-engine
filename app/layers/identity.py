"""LAYER 2: the secret user ID.

Turns "telegram" + "123456789" into a private label like "a91f3c7d2e84b1f0".
- The same person always gets the same label, so we can count their messages and strikes.
- Nobody can work out the real chat ID from the label, and nobody can make a label for
  someone else, because both need our secret (ID_SECRET in .env).

A plain hash would NOT be safe: chat IDs are short numbers, so an attacker could try
every number and compare. HMAC mixes in a secret, so that guessing is not possible.
"""
import hashlib
import hmac

from app.core.config import get_settings

# 16 hex characters = 64 bits. With 1 million users the chance that any two share a label is about 1 in 37 million.
ID_LENGTH = 16


def make_user_key(channel: str, user_id: str, secret: str | None = None) -> str:
    # "channel" can only be one of our fixed words (no ":" inside), so "channel:user_id" is never ambiguous.
    message = f"{channel}:{user_id}".encode("utf-8")
    if secret is None:
        secret = get_settings().id_secret
    key = secret.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()[:ID_LENGTH]
