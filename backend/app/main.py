from __future__ import annotations

import json
import secrets
import sqlite3
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import db, gemini, totp
from .astro import IST, ashtakoot, drishti_brief, natal_chart, panchang_now
from .auth import (
    attach_pending_cookie,
    attach_session_cookie,
    clear_auth_cookies,
    client_ip,
    consume_otp_ticket,
    create_session,
    find_user_by_email,
    find_user_by_id,
    get_user,
    issue_otp,
    optional_user,
    pending_user_id,
    consume_pending,
    revoke_session,
    rollback_otp,
    complete_email_otp,
    SESSION_COOKIE,
    validate_dob,
    validate_email,
    validate_name,
    validate_tob,
    verify_password,
)
from .errors import (
    AppError,
    GENERIC,
    INVALID_EMAIL,
    from_app_error,
    json_error,
    leaky,
    new_request_id,
    request_id_var,
    safe_user_message,
)
from .data import ASTROLOGERS, CITIES, MELAPAK_MODES, PRIYA, SAMADHAN
from . import mail
from .settings import frontend_origin_regex, frontend_origins

gemini.load_env()

app = FastAPI(title="AstroLive", version="1.2.0")
_cors: dict[str, Any] = {
    "allow_origins": frontend_origins(),
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
_origin_re = frontend_origin_regex()
if _origin_re:
    _cors["allow_origin_regex"] = _origin_re
app.add_middleware(CORSMiddleware, **_cors)

User = Annotated[dict, Depends(get_user)]
MAX_BODY = 32_768
ModeKey = Literal["bandhan", "saha", "mitra", "kula"]


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id") or new_request_id()
    request.state.request_id = rid
    token = request_id_var.set(rid)
    try:
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > MAX_BODY:
                    return json_error(413, "INVALID", GENERIC, dev_detail="payload too large")
            except ValueError:
                return json_error(400, "INVALID", GENERIC, dev_detail="bad content-length")
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response
    finally:
        request_id_var.reset(token)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return from_app_error(exc)


@app.exception_handler(StarletteHTTPException)
async def http_exc(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and detail.get("userMessage"):
        return json_error(
            exc.status_code,
            str(detail.get("code") or "ERROR"),
            str(detail["userMessage"]),
            dev_detail=str(detail.get("devDetail") or ""),
        )
    raw = "; ".join(str(item) for item in detail) if isinstance(detail, list) else (str(detail) if detail else GENERIC)
    user = GENERIC if leaky(raw) else safe_user_message(raw)
    code = "AUTH_REQUIRED" if exc.status_code == 401 else "ERROR"
    if exc.status_code == 429:
        code = "RATE_LIMITED"
    return json_error(exc.status_code, code, user, dev_detail=raw)


@app.exception_handler(RequestValidationError)
async def validation_exc(_request: Request, exc: RequestValidationError) -> JSONResponse:
    for err in exc.errors():
        loc = err.get("loc", [])
        if "email" in loc:
            return json_error(422, "INVALID_EMAIL", INVALID_EMAIL, dev_detail=str(err.get("msg") or ""))
        if "code" in loc:
            return json_error(401, "CODE_INVALID", "That code isn't right. 5 attempts left.", dev_detail=str(err.get("msg") or ""))
    return json_error(422, "INVALID", GENERIC, dev_detail=str(exc.errors()))


@app.exception_handler(Exception)
async def unhandled_exc(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, AppError):
        return from_app_error(exc)
    if isinstance(exc, StarletteHTTPException):
        return await http_exc(request, exc)
    if isinstance(exc, RequestValidationError):
        return await validation_exc(request, exc)
    from .errors import log as errlog

    errlog.exception("unhandled request=%s", request_id_var.get())
    return json_error(500, "ERROR", GENERIC, dev_detail=f"{type(exc).__name__}: {exc}")


class OtpSendIn(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return validate_email(value)


class OtpVerifyIn(BaseModel):
    email: str
    code: str = Field(min_length=6, max_length=6)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return validate_email(value)

    @field_validator("code")
    @classmethod
    def _code(cls, value: str) -> str:
        digits = value.strip()
        if not digits.isdigit() or len(digits) != 6:
            raise ValueError("Enter the 6-digit code from your email.")
        return digits


class RegisterIn(BaseModel):
    ticket: str = Field(min_length=16, max_length=80)
    name: str
    dob: str
    tob: str
    place: str = Field(min_length=2, max_length=80)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    gotra: str = Field(default="", max_length=40)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return validate_name(value)

    @field_validator("dob")
    @classmethod
    def _dob(cls, value: str) -> str:
        return validate_dob(value)

    @field_validator("tob")
    @classmethod
    def _tob(cls, value: str) -> str:
        return validate_tob(value)


class LoginIn(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return validate_email(value)


class TotpCodeIn(BaseModel):
    code: str = Field(min_length=4, max_length=16)


class MelapakIn(BaseModel):
    mode: ModeKey = "bandhan"


class MelapakJoinIn(BaseModel):
    name: str = ""
    dob: str = ""
    tob: str = ""
    place: str = Field(default="Delhi", min_length=2, max_length=80)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        text = value.strip()
        return validate_name(text) if text else ""

    @field_validator("dob")
    @classmethod
    def _dob(cls, value: str) -> str:
        return validate_dob(value) if value.strip() else ""

    @field_validator("tob")
    @classmethod
    def _tob(cls, value: str) -> str:
        return validate_tob(value) if value.strip() else ""


class BookIn(BaseModel):
    item_id: str = Field(pattern=r"^[a-z0-9_-]{2,40}$")


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    astrologer_id: str = Field(default="ak", min_length=1, max_length=16)

    @field_validator("message")
    @classmethod
    def _message(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Message cannot be empty.")
        return text


class ChatStartIn(BaseModel):
    astrologer_id: str = Field(default="ak", min_length=1, max_length=16)


def _city(place: str, lat: float | None, lon: float | None) -> tuple[str, float, float]:
    if lat is not None and lon is not None:
        return place.strip(), lat, lon
    hit = next((c for c in CITIES if c["name"].lower() == place.lower()), None)
    if not hit:
        hit = next((c for c in CITIES if place.lower() in c["name"].lower()), None)
    if not hit:
        raise HTTPException(400, "Unknown place. Choose a city from the list.")
    return hit["name"], hit["lat"], hit["lon"]


def _new_id() -> str:
    return "USR" + secrets.token_hex(3).upper()


def _astrologer(aid: str) -> dict:
    hit = next((a for a in ASTROLOGERS if a["id"] == aid), None)
    if not hit:
        raise HTTPException(404, "Astrologer not found.")
    return hit


def _public_user(u: dict) -> dict[str, Any]:
    chart = u["chart"]
    return {
        "id": u["id"],
        "name": u["name"],
        "email": u.get("email") or "",
        "dob": u["dob"],
        "tob": u["tob"],
        "place": u["place"],
        "gotra": u.get("gotra") or "",
        "wallet": u["wallet"],
        "streak": u["streak"],
        "upay_date": u.get("upay_date") or "",
        "lagna": chart["lagna"],
        "nakshatra": chart["nakshatra"],
        "totp_enabled": totp.totp_enabled(u["id"]),
    }


def _session_payload(user: dict) -> dict:
    return {"user": _public_user(user)}


def _insert_user(
    *,
    name: str,
    dob: str,
    tob: str,
    place: str,
    lat: float,
    lon: float,
    gotra: str = "",
    email: str = "",
    password_hash: str = "",
) -> dict:
    try:
        chart = natal_chart(dob, tob, lat, lon)
    except ValueError as exc:
        raise HTTPException(400, f"Invalid date or time: {exc}") from exc
    uid = _new_id()
    conn = db.connect()
    try:
        conn.execute(
            """INSERT INTO users
               (id, name, dob, tob, place, lat, lon, gotra, chart_json, email, password_hash)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (uid, name, dob, tob, place, lat, lon, gotra, json.dumps(chart), email, password_hash),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.close()
        raise HTTPException(409, "An account with this email already exists.") from exc
    row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return db.user_to_dict(row)


def _public_messages(rows: list[dict]) -> list[dict]:
    return [
        r
        for r in rows
        if not (r["role"] == "user" and str(r["content"]).startswith("Namaste. I am"))
    ]


def _chat_rows(user_id: str, astrologer_id: str) -> list[dict]:
    conn = db.connect()
    rows = conn.execute(
        """SELECT id, role, content, created_at FROM chat_messages
           WHERE user_id=? AND astrologer_id=? ORDER BY id ASC""",
        (user_id, astrologer_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _append_chat(user_id: str, astrologer_id: str, role: str, content: str) -> None:
    conn = db.connect()
    conn.execute(
        "INSERT INTO chat_messages (user_id, astrologer_id, role, content) VALUES (?,?,?,?)",
        (user_id, astrologer_id, role, content),
    )
    conn.commit()
    conn.close()


def _run_model(user: dict, astrologer: dict, history: list[dict[str, str]]) -> str:
    pan = panchang_now(user["lat"], user["lon"], user["chart"]["lagna"])
    system = gemini.system_prompt(user, astrologer, pan)
    try:
        return gemini.generate_reply(system, history)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, "Consult is temporarily unavailable. Try again in a moment.") from exc


@app.on_event("startup")
def _startup() -> None:
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    gemini.load_env()
    db.init_db()
    mail.warn_if_unconfigured()


@app.api_route("/", methods=["GET", "HEAD"])
@app.api_route("/health", methods=["GET", "HEAD"])
def root() -> dict[str, str]:
    return {"status": "ok", "service": "AstroLive API", "health": "/api/health"}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "lahiri-sidereal"}


@app.get("/api/cities")
def cities() -> list[dict]:
    return CITIES


@app.get("/api/modes")
def modes() -> dict:
    return MELAPAK_MODES


def _otp_send(body: OtpSendIn, request: Request) -> dict:
    code, retry_after = issue_otp(body.email, client_ip(request))
    try:
        mail.send_otp(body.email, code)
    except AppError:
        rollback_otp(body.email)
        raise
    return {"ok": True, "sent": True, "retry_after": retry_after, "expires_in": 600}


@app.post("/api/auth/otp/send")
def otp_send(body: OtpSendIn, request: Request) -> dict:
    return _otp_send(body, request)


@app.post("/api/auth/request-code")
def request_code(body: OtpSendIn, request: Request) -> dict:
    return _otp_send(body, request)


@app.post("/api/auth/otp/verify")
def otp_verify(body: OtpVerifyIn, request: Request, response: Response) -> dict:
    result = complete_email_otp(body.email, body.code, request.headers.get("user-agent", ""))
    if result["kind"] == "session":
        attach_session_cookie(response, result["raw"])
        return {"needs_profile": False, "needs_totp": False, **_session_payload(result["user"])}
    if result["kind"] == "totp":
        attach_pending_cookie(response, result["raw"])
        return {"needs_profile": False, "needs_totp": True}
    return {
        "needs_profile": True,
        "needs_totp": False,
        "ticket": result["ticket"],
        "email": body.email,
    }


@app.post("/api/auth/register")
def register(body: RegisterIn, request: Request, response: Response) -> dict:
    email = consume_otp_ticket(body.ticket)
    if find_user_by_email(email):
        raise HTTPException(409, "An account with this email already exists.")
    place, lat, lon = _city(body.place, body.lat, body.lon)
    user = _insert_user(
        name=body.name,
        dob=body.dob,
        tob=body.tob,
        place=place,
        lat=lat,
        lon=lon,
        gotra=body.gotra.strip(),
        email=email,
        password_hash="",
    )
    raw = create_session(user["id"], request.headers.get("user-agent", ""))
    attach_session_cookie(response, raw)
    return _session_payload(user)


@app.post("/api/onboard")
def onboard(body: RegisterIn, request: Request, response: Response) -> dict:
    """Same as register — kept so older clients get a clear validation error instead of a silent guest user."""
    return register(body, request, response)


@app.post("/api/auth/login")
def login(body: LoginIn, request: Request, response: Response) -> dict:
    conn = db.connect()
    row = conn.execute("SELECT * FROM users WHERE lower(email)=?", (body.email,)).fetchone()
    stored = row["password_hash"] if row else ""
    conn.close()
    if not row or not stored or not verify_password(body.password, stored):
        raise HTTPException(401, "Email or password is wrong.")
    user = db.user_to_dict(row)
    if totp.totp_enabled(user["id"]):
        from .auth import create_pending_2fa

        attach_pending_cookie(response, create_pending_2fa(user["id"]))
        return {"needs_totp": True, "needs_profile": False}
    raw = create_session(user["id"], request.headers.get("user-agent", ""))
    attach_session_cookie(response, raw)
    return {**_session_payload(user), "needs_totp": False}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict:
    raw = request.cookies.get(SESSION_COOKIE)
    if raw:
        revoke_session(raw)
    clear_auth_cookies(response)
    return {"ok": True}


@app.get("/api/auth/totp/status")
def totp_status(u: User) -> dict:
    return totp.status(u["id"])


@app.post("/api/auth/totp/setup")
def totp_setup(u: User) -> dict:
    return totp.setup(u["id"], u.get("email") or "")


@app.post("/api/auth/totp/enable")
def totp_enable(body: TotpCodeIn, u: User) -> dict:
    codes = totp.enable(u["id"], body.code)
    return {"ok": True, "recovery_codes": codes, "enabled": True}


@app.post("/api/auth/totp/verify")
def totp_verify(body: TotpCodeIn, request: Request, response: Response) -> dict:
    uid = pending_user_id(request)
    raw_session = totp.verify_login(uid, body.code)
    pending = request.cookies.get("astrolive_pending")
    if pending:
        consume_pending(pending)
    attach_session_cookie(response, raw_session)
    user = find_user_by_id(uid)
    if not user:
        raise HTTPException(401, "Please sign in again.")
    return {**_session_payload(user), "needs_totp": False}


@app.post("/api/auth/totp/disable")
def totp_disable(body: TotpCodeIn, u: User) -> dict:
    totp.disable(u["id"], body.code)
    return {"ok": True, "enabled": False}


@app.get("/api/me")
def me(u: User) -> dict:
    return _public_user(u)


@app.get("/api/panchang")
def panchang(u: User) -> dict:
    chart = u["chart"]
    pan = panchang_now(u["lat"], u["lon"], chart["lagna"])
    today = datetime.now(IST).date().isoformat()
    pan["streak"] = u["streak"]
    pan["upay_done"] = u["upay_date"] == today
    pan["wallet"] = u["wallet"]
    pan["user"] = {"name": u["name"], "lagna": chart["lagna"], "nakshatra": chart["nakshatra"]}
    return pan


@app.post("/api/upay/complete")
def upay_complete(u: User) -> dict:
    today = datetime.now(IST).date().isoformat()
    if u["upay_date"] == today:
        return {"streak": u["streak"], "upay_done": True, "already": True}
    streak = int(u["streak"]) + 1
    conn = db.connect()
    conn.execute("UPDATE users SET streak=?, upay_date=? WHERE id=?", (streak, today, u["id"]))
    conn.commit()
    conn.close()
    return {"streak": streak, "upay_done": True, "already": False}


@app.get("/api/kundali")
def kundali(u: User) -> dict:
    return {"chart": u["chart"], "name": u["name"], "place": u["place"], "dob": u["dob"], "tob": u["tob"]}


@app.get("/api/astrologers")
def astrologers() -> list[dict]:
    return ASTROLOGERS


@app.get("/api/drishti")
def drishti(u: User) -> dict:
    brief = drishti_brief(u["chart"])
    brief["astrologer"] = ASTROLOGERS[0]
    return brief


@app.get("/api/chat")
def chat_history(u: User, astrologer_id: str = "ak") -> dict:
    astro = _astrologer(astrologer_id)
    return {"astrologer": astro, "messages": _public_messages(_chat_rows(u["id"], astrologer_id))}


@app.post("/api/chat/start")
def chat_start(body: ChatStartIn, u: User) -> dict:
    astro = _astrologer(body.astrologer_id)
    existing = _chat_rows(u["id"], body.astrologer_id)
    if existing:
        return {"astrologer": astro, "messages": _public_messages(existing), "fresh": False}
    seed = (
        f"Namaste. I am {u['name']}. Please open this consultation: greet me by name, "
        "give a short 3-sentence reading of my Lagna, Chandra nakshatra and today's muhurat, "
        "then ask one focused question."
    )
    reply = _run_model(u, astro, [{"role": "user", "content": seed}])
    _append_chat(u["id"], body.astrologer_id, "user", seed)
    _append_chat(u["id"], body.astrologer_id, "assistant", reply)
    return {"astrologer": astro, "messages": _public_messages(_chat_rows(u["id"], body.astrologer_id)), "fresh": True}


@app.post("/api/chat")
def chat_send(body: ChatIn, u: User) -> dict:
    astro = _astrologer(body.astrologer_id)
    prior = _chat_rows(u["id"], body.astrologer_id)
    history = [{"role": r["role"], "content": r["content"]} for r in prior]
    history.append({"role": "user", "content": body.message})
    reply = _run_model(u, astro, history)
    _append_chat(u["id"], body.astrologer_id, "user", body.message)
    _append_chat(u["id"], body.astrologer_id, "assistant", reply)
    return {"reply": reply, "astrologer": astro, "messages": _public_messages(_chat_rows(u["id"], body.astrologer_id))}


@app.get("/api/samadhan")
def samadhan() -> list[dict]:
    return SAMADHAN


@app.post("/api/samadhan/book")
def book(body: BookIn, u: User) -> dict:
    item = next((s for s in SAMADHAN if s["id"] == body.item_id), None)
    if not item:
        raise HTTPException(404, "That offering is not on the list.")
    bid = "BK" + uuid.uuid4().hex[:8].upper()
    conn = db.connect()
    conn.execute(
        "INSERT INTO bookings (id, user_id, item_id, title, price) VALUES (?,?,?,?,?)",
        (bid, u["id"], item["id"], item["title"], item["price"]),
    )
    new_wallet = max(0, int(u["wallet"]) - min(item["price"], 180))
    conn.execute("UPDATE users SET wallet=? WHERE id=?", (new_wallet, u["id"]))
    conn.commit()
    conn.close()
    return {"booking_id": bid, "title": item["title"], "price": item["price"], "wallet": new_wallet, "status": "sankalp_queued"}


@app.get("/api/bookings")
def bookings(u: User) -> list[dict]:
    conn = db.connect()
    rows = conn.execute(
        "SELECT id, item_id, title, price, created_at FROM bookings WHERE user_id=? ORDER BY created_at DESC",
        (u["id"],),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/melapak/link")
def melapak_link(body: MelapakIn, u: User) -> dict:
    token = secrets.token_urlsafe(8)
    conn = db.connect()
    conn.execute(
        "INSERT INTO matches (token, mode, host_id) VALUES (?,?,?)",
        (token, body.mode, u["id"]),
    )
    conn.commit()
    conn.close()
    return {
        "token": token,
        "mode": body.mode,
        "path": f"/melapak/{token}",
        "host": u["name"],
    }


@app.get("/api/melapak/demo/priya")
def demo_priya(u: User) -> dict:
    priya_chart = natal_chart(PRIYA["dob"], PRIYA["tob"], PRIYA["lat"], PRIYA["lon"])
    result = ashtakoot(priya_chart, u["chart"])
    result["a"] = {"name": u["name"], "nakshatra": u["chart"]["nakshatra"], "rashi": u["chart"]["chandra_rashi"]}
    result["b"] = {"name": PRIYA["name"], "nakshatra": priya_chart["nakshatra"], "rashi": priya_chart["chandra_rashi"]}
    return result


def _match_payload(token: str) -> dict:
    if len(token) < 6 or len(token) > 40:
        raise HTTPException(404, "Link expired or invalid.")
    conn = db.connect()
    row = conn.execute("SELECT * FROM matches WHERE token=?", (token,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Link expired or invalid.")
    host = conn.execute("SELECT * FROM users WHERE id=?", (row["host_id"],)).fetchone()
    conn.close()
    mode = MELAPAK_MODES[row["mode"]]
    result = json.loads(row["result_json"]) if row["result_json"] else None
    return {
        "token": token,
        "mode": row["mode"],
        "mode_meta": mode,
        "host_name": host["name"] if host else "Someone",
        "guest_name": row["guest_name"],
        "result": result,
        "complete": result is not None,
    }


@app.get("/api/melapak/{token}")
def melapak_get(token: str) -> dict:
    return _match_payload(token)


@app.post("/api/melapak/{token}/join")
def melapak_join(
    token: str,
    body: MelapakJoinIn,
    request: Request,
    response: Response,
) -> dict:
    conn = db.connect()
    row = conn.execute("SELECT * FROM matches WHERE token=?", (token,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Link expired or invalid.")
    host_row = conn.execute("SELECT * FROM users WHERE id=?", (row["host_id"],)).fetchone()
    conn.close()
    if not host_row:
        raise HTTPException(404, "This match no longer exists.")
    host = db.user_to_dict(host_row)

    signed_in = optional_user(request)

    if row["result_json"]:
        result = json.loads(row["result_json"])
        if signed_in and row["guest_id"] == signed_in["id"]:
            return {"guest_id": signed_in["id"], "result": result, "user": _public_user(signed_in)}
        raise HTTPException(409, "This match is already complete.")

    new_guest = False
    if signed_in:
        if signed_in["id"] == host["id"]:
            raise HTTPException(400, "You cannot join your own Melapak link.")
        guest = signed_in
    else:
        if not body.name or not body.dob or not body.tob:
            raise HTTPException(422, "Name, date and time of birth are required.")
        place, lat, lon = _city(body.place, body.lat, body.lon)
        guest = _insert_user(
            name=body.name,
            dob=body.dob,
            tob=body.tob,
            place=place,
            lat=lat,
            lon=lon,
        )
        new_guest = True

    result_out = {
        **ashtakoot(guest["chart"], host["chart"]),
        "a": {
            "name": host["name"],
            "nakshatra": host["chart"]["nakshatra"],
            "rashi": host["chart"]["chandra_rashi"],
            "lagna": host["chart"]["lagna"],
        },
        "b": {
            "name": guest["name"],
            "nakshatra": guest["chart"]["nakshatra"],
            "rashi": guest["chart"]["chandra_rashi"],
            "lagna": guest["chart"]["lagna"],
        },
        "mode": row["mode"],
    }
    conn = db.connect()
    conn.execute(
        "UPDATE matches SET guest_id=?, guest_name=?, result_json=? WHERE token=?",
        (guest["id"], guest["name"], json.dumps(result_out), token),
    )
    conn.commit()
    conn.close()
    if new_guest:
        attach_session_cookie(response, create_session(guest["id"], request.headers.get("user-agent", "")))
    return {"guest_id": guest["id"], "result": result_out, "user": _public_user(guest)}


@app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
def unknown_path(path: str) -> dict[str, str]:
    if path.startswith("api/") or path == "api":
        raise HTTPException(404, "Not Found")
    return {
        "status": "ok",
        "service": "AstroLive API",
        "health": "/api/health",
        "message": "This host is the API. Open the Vercel frontend for the app.",
    }
