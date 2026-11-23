"""Closet persistence for Streamlit Community Cloud.

Approach: each visitor gets a random closet id (128-bit, URL-safe) kept in the page URL as ?c=<id>.  The closet,
style profile, photo thumbnails and shop list are saved as one small JSON file on the app server, named by that id.
A browser refresh keeps the URL, so the closet comes back; bookmarking the URL brings it back later too.

Trade-offs (documented in README):
  * Community Cloud's disk is ephemeral: a redeploy, reboot or the app going to sleep wipes every saved closet.
    (Browser localStorage would survive that, but needs a third-party component whose value only arrives after an
    extra rerun; a hosted DB would need an account + secrets.  For a class prototype the file approach is simplest.)
  * Anyone who has the full URL (with ?c=...) can open that closet, like an unlisted link.  Don't share it.
  * Only thumbnails (<=240px JPEG) are stored, never the full photo, and files older than MAX_AGE_DAYS are pruned.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
import time
from pathlib import Path

TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,40}$")
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_AGE_DAYS = 30
MAX_FILES = 2000


def data_dir() -> Path:
    d = Path(os.environ.get("FASHIONISTA_DATA_DIR") or Path(tempfile.gettempdir()) / "fashionista-closets")
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_token() -> str:
    return secrets.token_urlsafe(16)


def valid_token(token) -> bool:
    return isinstance(token, str) and bool(TOKEN_RE.match(token))


def _path(token) -> Path:
    if not valid_token(token):
        raise ValueError("bad closet id")
    return data_dir() / f"{token}.json"


def exists(token) -> bool:
    return valid_token(token) and _path(token).exists()


def load(token) -> dict | None:
    """The saved closet for this id, or None (unknown id, unreadable or corrupt file)."""
    if not valid_token(token):
        return None
    try:
        p = _path(token)
        if not p.exists() or p.stat().st_size > MAX_FILE_BYTES:
            return None
        data = json.loads(p.read_text("utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def save(token, data: dict) -> bool:
    """Atomic write (temp file + rename).  False if it couldn't be saved (too big, disk error)."""
    try:
        raw = json.dumps(data, separators=(",", ":"))
        if len(raw) > MAX_FILE_BYTES:
            return False
        p = _path(token)
        tmp = p.with_suffix(f".{secrets.token_hex(4)}.tmp")
        tmp.write_text(raw, "utf-8")
        os.replace(tmp, p)
        return True
    except (OSError, ValueError, TypeError):
        return False


def prune(now=None) -> int:
    """Delete saves older than MAX_AGE_DAYS (and the oldest beyond MAX_FILES).  Best effort; returns count."""
    now = now or time.time()
    try:
        files = sorted(data_dir().glob("*.json"), key=lambda f: f.stat().st_mtime)
    except OSError:
        return 0
    old = [f for f in files if now - f.stat().st_mtime > MAX_AGE_DAYS * 86400]
    old += files[len(old):max(len(files) - MAX_FILES, len(old))]
    n = 0
    for f in old:
        try:
            f.unlink(); n += 1
        except OSError:
            pass
    return n
