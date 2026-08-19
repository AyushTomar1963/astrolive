"""Gemini REST client for Jyotish Drishti chat."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

MODELS = (
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-1.5-flash",
)


def load_env() -> None:
    if not ENV_PATH.exists():
        return
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ[key.strip()] = val.strip().strip('"').strip("'")


def _api_key() -> str:
    load_env()
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set in backend/.env")
    return key


def _preferred_models() -> list[str]:
    load_env()
    first = os.environ.get("GEMINI_MODEL", "").strip()
    ordered = [first] + [m for m in MODELS if m != first] if first else list(MODELS)
    return [m for m in ordered if m]


def chart_context(user: dict[str, Any]) -> str:
    chart = user["chart"]
    lines = [
        f"Name: {user['name']}",
        f"Birth: {user['dob']} {user['tob']} IST at {user['place']}",
        f"Lagna: {chart['lagna']} ({chart.get('lagna_en', '')})",
        f"Chandra rashi: {chart['chandra_rashi']} · Nakshatra {chart['nakshatra']} pada {chart.get('pada')}",
        f"Mangal dosha: {chart['mangal']['status']}",
        "Grahas:",
    ]
    for p in chart.get("positions", []):
        lines.append(
            f"  {p['graha']}: {p['rashi']} H{p['house']} {p.get('dms', '')} · {p.get('nakshatra', '')}"
        )
    return "\n".join(lines)


def system_prompt(user: dict[str, Any], astrologer: dict[str, Any], panchang: dict[str, Any] | None) -> str:
    pan = ""
    if panchang:
        pan = (
            f"Today: {panchang.get('date')} {panchang.get('now')}. "
            f"Tithi {panchang.get('tithi')}. Nakshatra {panchang.get('nakshatra')}. "
            f"Abhijit {panchang.get('abhijit', {})}. Rahu Kaal {panchang.get('rahu_kaal', {})}. "
            f"Upay: {panchang.get('upay', '')}"
        )
    return f"""You are {astrologer['name']}, a {astrologer['speciality']} practitioner with {astrologer['years']} years of experience.
You are speaking inside AstroLive's Jyotish Drishti consultation chat.

Voice: calm, precise, slightly formal Indian English mixed with a few Sanskrit terms (Lagna, Chandra, muhurat, upay). Never theatrical, never fear-mongering.

Hard rules:
- Do not diagnose disease, give legal advice, or promise financial outcomes.
- Do not tell anyone they are cursed or doomed.
- Ground every remark in the natal chart and today's panchang below.
- Keep replies under 140 words unless the user asks for a breakdown.
- Offer one practical upay or timing suggestion when relevant.
- If asked for medical/legal/finance guarantees, refuse and redirect to a qualified professional.

NATIVE CHART
{chart_context(user)}

TODAY'S PANCHANG
{pan or "(not supplied)"}
"""


def _call_model(model: str, key: str, system: str, history: list[dict[str, str]]) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={urllib.parse.quote(key)}"
    )
    contents: list[dict[str, Any]] = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 700, "topP": 0.9},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini {model} HTTP {e.code}: {body[:400]}") from e
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini {model} returned no candidates: {str(data)[:300]}")
    parts = candidates[0].get("content", {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError(f"Gemini {model} empty text")
    return text


def generate_reply(system: str, history: list[dict[str, str]]) -> str:
    key = _api_key()
    errors: list[str] = []
    for model in _preferred_models():
        try:
            return _call_model(model, key, system, history)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            continue
    raise RuntimeError("All Gemini models failed. " + " | ".join(errors[:3]))
