from __future__ import annotations

import os

from .gemini import load_env


def _csv(name: str) -> list[str]:
    load_env()
    return [part.strip().rstrip("/") for part in os.environ.get(name, "").split(",") if part.strip()]


def frontend_origins() -> list[str]:
    extra = _csv("FRONTEND_ORIGINS")
    defaults = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    seen: list[str] = []
    for origin in extra + defaults:
        if origin not in seen:
            seen.append(origin)
    return seen


def frontend_origin_regex() -> str | None:
    load_env()
    raw = os.environ.get("FRONTEND_ORIGIN_REGEX", "").strip()
    return raw or None


def cookie_samesite() -> str:
    load_env()
    raw = os.environ.get("COOKIE_SAMESITE", "lax").strip().lower()
    if raw not in ("lax", "strict", "none"):
        return "lax"
    return raw
