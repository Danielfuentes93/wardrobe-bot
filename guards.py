"""Safety rails for the public deployment: secrets, LLM budgets, passcode, photo handling.

Nothing here writes to disk, prints, or logs a secret.
"""
from __future__ import annotations

import hmac
import io
import os
import threading
from datetime import datetime, timezone

import streamlit as st

SESSION_LLM_LIMIT = 10          # Grok messages per visitor session
MAX_MESSAGE_CHARS = 400         # per chat message
DEFAULT_DAILY_CAP = 300         # Grok calls per UTC day across ALL visitors (override: secret DAILY_LLM_CAP)
DEFAULT_MAX_TOKENS = 600        # cap on the model's reply (override: secret LLM_MAX_TOKENS)
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PHOTO_PX = 800
THUMB_PX = 240
MAX_ITEMS = 30                  # closet size per visitor
MAX_NAME_CHARS = 40
LLM_TIMEOUT_S = 20
DOWN_MINUTES = 10               # after an auth/credit error, stop calling the API for everyone this long
PERSISTENT_ERROR_STATUS = {401, 402, 403, 429}


# ---------------------------------------------------------------- secrets
def get_secret(name: str, default=None):
    """st.secrets first (Streamlit Cloud / .streamlit/secrets.toml), then environment variables."""
    try:
        if name in st.secrets:
            val = st.secrets[name]
            if val is not None and str(val) != "":
                return val
    except Exception:  # no secrets file at all, or an unreadable one
        pass
    val = os.environ.get(name)
    return val if val not in (None, "") else default


def int_secret(name: str, default: int) -> int:
    try:
        v = int(str(get_secret(name, default)).strip())
        return v if v >= 0 else default
    except (TypeError, ValueError):
        return default


def llm_model() -> str:
    base = str(get_secret("OPENAI_BASE_URL", ""))
    return str(get_secret("OPENAI_MODEL", "grok-3-mini" if "x.ai" in base else "gpt-4o-mini"))


def make_llm_client():
    """OpenAI-compatible client built from secrets/env, or None (offline) if there is no key / no package."""
    key = get_secret("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(api_key=str(key), base_url=get_secret("OPENAI_BASE_URL") or None,
                  timeout=LLM_TIMEOUT_S, max_retries=1)


# ---------------------------------------------------------------- global daily budget
class DailyBudget:
    """Counts LLM calls for all visitors; resets when the UTC date changes."""

    def __init__(self):
        self.lock = threading.Lock()
        self.day = None
        self.used = 0
        self.down_until = None  # datetime, set after auth/credit errors

    @staticmethod
    def _now(now):
        return now or datetime.now(timezone.utc)

    def _roll(self, now):
        if now.date() != self.day:
            self.day, self.used = now.date(), 0

    def try_consume(self, cap: int, now=None) -> bool:
        """Reserve one LLM call.  False when the cap is reached (or the API was marked down)."""
        now = self._now(now)
        with self.lock:
            self._roll(now)
            if self.down_until and now < self.down_until:
                return False
            if self.used >= cap:
                return False
            self.used += 1
            return True

    def mark_down(self, minutes: int = DOWN_MINUTES, now=None):
        from datetime import timedelta
        now = self._now(now)
        with self.lock:
            self.down_until = now + timedelta(minutes=minutes)

    def status(self, cap: int, now=None) -> dict:
        now = self._now(now)
        with self.lock:
            self._roll(now)
            return {"used": self.used, "cap": cap, "remaining": max(cap - self.used, 0),
                    "down": bool(self.down_until and now < self.down_until)}


@st.cache_resource
def get_budget() -> DailyBudget:
    """One DailyBudget per server process (shared by every visitor session).  Lost on app restart/sleep."""
    return DailyBudget()


# ---------------------------------------------------------------- passcode gate
def passcode_required() -> bool:
    return bool(get_secret("APP_PASSCODE"))


def check_passcode(entered: str) -> bool:
    expected = str(get_secret("APP_PASSCODE", ""))
    if not expected:
        return True
    return hmac.compare_digest(entered.strip().encode(), expected.strip().encode())


# ---------------------------------------------------------------- chat input
def clean_message(text: str) -> tuple[str, bool]:
    """Strip control characters and cut to MAX_MESSAGE_CHARS.  Returns (text, was_truncated)."""
    text = "".join(ch for ch in str(text) if ch in "\n\t" or ch.isprintable()).strip()
    return text[:MAX_MESSAGE_CHARS], len(text) > MAX_MESSAGE_CHARS


# ---------------------------------------------------------------- photos
class PhotoError(ValueError):
    pass


def process_photo(raw: bytes) -> tuple[bytes, bytes]:
    """Validate an upload and return (jpeg <=800px, jpeg thumbnail).  Raises PhotoError with a friendly message."""
    from PIL import Image, ImageOps, UnidentifiedImageError
    if len(raw) > MAX_UPLOAD_BYTES:
        raise PhotoError(f"That photo is {len(raw) / 1048576:.1f} MB. The limit is 5 MB.")
    Image.MAX_IMAGE_PIXELS = 40_000_000  # refuse decompression bombs
    try:
        probe = Image.open(io.BytesIO(raw))
        probe.verify()
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError, ValueError):
        raise PhotoError("That file is not a readable image (use PNG, JPG or WebP).") from None
    out = []
    for px, q in ((MAX_PHOTO_PX, 85), (THUMB_PX, 80)):
        c = img.copy()
        c.thumbnail((px, px))
        buf = io.BytesIO()
        c.save(buf, "JPEG", quality=q)  # re-encoding also drops EXIF/location metadata
        out.append(buf.getvalue())
    return out[0], out[1]
