from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response

from . import db
from .errors import (
    AppError,
    GENERIC,
    code_expired,
    code_invalid,
    is_production,
    rate_limited,
    too_many_attempts,
)
from .settings import cookie_samesite

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DOB_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TOB_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")
PBKDF2_ROUNDS = 120_000
SESSION_DAYS = 30
SESSION_COOKIE = "astrolive_session"
PENDING_COOKIE = "astrolive_pending"

OTP_TTL_MIN = 10
OTP_RESEND_SEC = 60
OTP_MAX_ATTEMPTS = 5
OTP_EMAIL_HOUR_CAP = 5
OTP_IP_HOUR_CAP = 20
TICKET_TTL_MIN = 20
PENDING_TTL_MIN = 5


def validate_email(email: str) -> str:
    value = email.strip().lower()
    if not EMAIL_RE.match(value) or len(value) > 120:
        raise ValueError("Enter a valid email address.")
    return value


def validate_password(password: str) -> str:
    if len(password) < 8 or len(password) > 128:
        raise ValueError("Password must be 8-128 characters.")
    if password.strip() != password:
        raise ValueError("Password cannot start or end with spaces.")
    return password


def validate_dob(dob: str) -> str:
    if not DOB_RE.match(dob):
        raise ValueError("Date of birth must be YYYY-MM-DD.")
    try:
        dt = datetime.strptime(dob, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Date of birth is not a real calendar date.") from exc
    year = dt.year
    now_year = datetime.now().year
    if year < 1920 or year > now_year:
        raise ValueError("Date of birth is out of range.")
    if dt.date() > datetime.now().date():
        raise ValueError("Date of birth cannot be in the future.")
    return dob


def validate_tob(tob: str) -> str:
    value = tob.strip()
    if not TOB_RE.match(value):
        raise ValueError("Time of birth must be HH:MM in 24-hour form.")
    return value[:5]


def validate_name(name: str) -> str:
    value = " ".join(name.split())
    if len(value) < 2 or len(value) > 80:
        raise ValueError("Name must be 2–80 characters.")
    return value


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"{salt.hex()}:{dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(dk_hex)
    except (ValueError, AttributeError):
        return False
    got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return hmac.compare_digest(got, expected)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _append_env(name: str, value: str) -> None:
    from .gemini import ENV_PATH

    with ENV_PATH.open("a", encoding="utf-8") as fh:
        fh.write(f"\n{name}={value}\n")
    os.environ[name] = value


def _env_secret(name: str, nbytes: int = 32) -> str:
    from .gemini import load_env

    load_env()
    raw = os.environ.get(name, "").strip()
    if raw:
        return raw
    if is_production():
        raise AppError(500, "ERROR", GENERIC, f"{name} missing")
    raw = secrets.token_hex(nbytes)
    _append_env(name, raw)
    return raw


def otp_pepper() -> bytes:
    return _env_secret("OTP_PEPPER").encode("utf-8")


def hash_login_code(code: str) -> str:
    return hmac.new(otp_pepper(), code.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def mint_opaque_token() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")


def cookie_kwargs() -> dict:
    samesite = cookie_samesite()
    secure = is_production() or samesite == "none"
    return {
        "httponly": True,
        "secure": secure,
        "samesite": samesite,
        "path": "/",
    }


def attach_session_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        raw,
        max_age=SESSION_DAYS * 24 * 3600,
        **cookie_kwargs(),
    )
    response.delete_cookie(PENDING_COOKIE, path="/")


def attach_pending_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        PENDING_COOKIE,
        raw,
        max_age=PENDING_TTL_MIN * 60,
        **cookie_kwargs(),
    )


def clear_auth_cookies(response: Response) -> None:
    opts = cookie_kwargs()
    response.delete_cookie(SESSION_COOKIE, path=opts["path"], samesite=opts["samesite"], secure=opts["secure"])
    response.delete_cookie(PENDING_COOKIE, path=opts["path"], samesite=opts["samesite"], secure=opts["secure"])


def client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host[:64]
    return "0.0.0.0"


def create_session(user_id: str, user_agent: str = "") -> str:
    raw = mint_opaque_token()
    now = _now()
    conn = db.connect()
    conn.execute(
        """INSERT INTO auth_sessions
           (id, token_hash, user_id, expires_at, last_seen_at, user_agent, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            hash_token(raw),
            user_id,
            (now + timedelta(days=SESSION_DAYS)).isoformat(),
            now.isoformat(),
            (user_agent or "")[:240],
            now.isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return raw


def revoke_session(raw: str) -> None:
    if not raw:
        return
    conn = db.connect()
    conn.execute("DELETE FROM auth_sessions WHERE token_hash=?", (hash_token(raw),))
    conn.commit()
    conn.close()


def user_from_session(raw: str, user_agent: str = "") -> dict | None:
    if not raw:
        return None
    conn = db.connect()
    row = conn.execute(
        """SELECT s.id AS sid, s.expires_at AS sess_expires, s.created_at AS sess_created, u.*
           FROM auth_sessions s JOIN users u ON u.id = s.user_id
           WHERE s.token_hash=?""",
        (hash_token(raw),),
    ).fetchone()
    if not row:
        conn.close()
        return None
    try:
        expires = _parse_dt(row["sess_expires"])
        created = _parse_dt(row["sess_created"])
    except (TypeError, ValueError):
        conn.execute("DELETE FROM auth_sessions WHERE id=?", (row["sid"],))
        conn.commit()
        conn.close()
        return None
    now = _now()
    if expires < now or created + timedelta(days=SESSION_DAYS) < now:
        conn.execute("DELETE FROM auth_sessions WHERE id=?", (row["sid"],))
        conn.commit()
        conn.close()
        return None
    remaining = created + timedelta(days=SESSION_DAYS)
    conn.execute(
        """UPDATE auth_sessions SET last_seen_at=?, expires_at=?, user_agent=?
           WHERE id=?""",
        (
            now.isoformat(),
            remaining.isoformat(),
            (user_agent or "")[:240],
            row["sid"],
        ),
    )
    conn.commit()
    user = db.user_to_dict(row)
    conn.close()
    return user


def get_user(request: Request) -> dict:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        raise AppError(401, "AUTH_REQUIRED", "Please sign in again.", "no cookie")
    user = user_from_session(raw, request.headers.get("user-agent", ""))
    if not user:
        raise AppError(401, "AUTH_REQUIRED", "Please sign in again.", "session missing")
    return user


def optional_user(request: Request) -> dict | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    return user_from_session(raw, request.headers.get("user-agent", ""))


def pending_user_id(request: Request) -> str:
    raw = request.cookies.get(PENDING_COOKIE)
    if not raw:
        raise AppError(401, "AUTH_REQUIRED", "Please sign in again.", "no pending 2fa")
    conn = db.connect()
    row = conn.execute(
        "SELECT user_id, expires_at FROM pending_2fa WHERE token_hash=?",
        (hash_token(raw),),
    ).fetchone()
    if not row:
        conn.close()
        raise AppError(401, "AUTH_REQUIRED", "Please sign in again.", "pending missing")
    try:
        if _parse_dt(row["expires_at"]) < _now():
            conn.execute("DELETE FROM pending_2fa WHERE token_hash=?", (hash_token(raw),))
            conn.commit()
            conn.close()
            raise AppError(401, "AUTH_REQUIRED", "Please sign in again.", "pending expired")
    except AppError:
        raise
    except (TypeError, ValueError) as exc:
        conn.close()
        raise AppError(401, "AUTH_REQUIRED", "Please sign in again.", "pending bad expiry") from exc
    uid = row["user_id"]
    conn.close()
    return uid


def consume_pending(raw: str) -> None:
    conn = db.connect()
    conn.execute("DELETE FROM pending_2fa WHERE token_hash=?", (hash_token(raw),))
    conn.commit()
    conn.close()


def create_pending_2fa(user_id: str) -> str:
    raw = mint_opaque_token()
    conn = db.connect()
    conn.execute("DELETE FROM pending_2fa WHERE user_id=?", (user_id,))
    conn.execute(
        "INSERT INTO pending_2fa (token_hash, user_id, expires_at) VALUES (?,?,?)",
        (hash_token(raw), user_id, (_now() + timedelta(minutes=PENDING_TTL_MIN)).isoformat()),
    )
    conn.commit()
    conn.close()
    return raw


def _minutes_until(when: datetime) -> int:
    secs = max(1, int((when - _now()).total_seconds()))
    return max(1, (secs + 59) // 60)


def issue_otp(email: str, ip: str) -> tuple[str, int]:
    """Always issues a code for any well-formed email. Returns (code, retry_after)."""
    conn = db.connect()
    hour_ago = (_now() - timedelta(hours=1)).isoformat()
    email_n = conn.execute(
        "SELECT COUNT(*) AS n FROM login_codes WHERE email=? AND created_at >= ?",
        (email, hour_ago),
    ).fetchone()["n"]
    if int(email_n) >= OTP_EMAIL_HOUR_CAP:
        oldest = conn.execute(
            """SELECT created_at FROM login_codes
               WHERE email=? AND created_at >= ? ORDER BY created_at ASC LIMIT 1""",
            (email, hour_ago),
        ).fetchone()
        conn.close()
        wait_until = _parse_dt(oldest["created_at"]) + timedelta(hours=1) if oldest else _now() + timedelta(hours=1)
        raise rate_limited(_minutes_until(wait_until), "hourly email cap")
    ip_n = conn.execute(
        "SELECT COUNT(*) AS n FROM login_codes WHERE request_ip=? AND created_at >= ?",
        (ip, hour_ago),
    ).fetchone()["n"]
    if int(ip_n) >= OTP_IP_HOUR_CAP:
        conn.close()
        raise rate_limited(60, "hourly ip cap")
    last = conn.execute(
        "SELECT created_at FROM login_codes WHERE email=? ORDER BY created_at DESC LIMIT 1",
        (email,),
    ).fetchone()
    if last:
        try:
            sent = _parse_dt(last["created_at"])
            wait = OTP_RESEND_SEC - int((_now() - sent).total_seconds())
            if wait > 0:
                conn.close()
                raise rate_limited(max(1, (wait + 59) // 60), f"cooldown {wait}s")
        except AppError:
            raise
        except (TypeError, ValueError):
            pass
    code = f"{secrets.randbelow(1_000_000):06d}"
    now = _now()
    row_id = str(uuid.uuid4())
    conn.execute(
        "UPDATE login_codes SET consumed_at=? WHERE email=? AND consumed_at IS NULL",
        (now.isoformat(), email),
    )
    conn.execute(
        """INSERT INTO login_codes
           (id, email, code_hash, expires_at, attempts, consumed_at, request_ip, created_at)
           VALUES (?,?,?,?,?,NULL,?,?)""",
        (
            row_id,
            email,
            hash_login_code(code),
            (now + timedelta(minutes=OTP_TTL_MIN)).isoformat(),
            0,
            ip,
            now.isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return code, OTP_RESEND_SEC


def rollback_otp(email: str) -> None:
    conn = db.connect()
    row = conn.execute(
        """SELECT id FROM login_codes WHERE email=? AND consumed_at IS NULL
           ORDER BY created_at DESC LIMIT 1""",
        (email,),
    ).fetchone()
    if row:
        conn.execute("DELETE FROM login_codes WHERE id=?", (row["id"],))
        conn.commit()
    conn.close()


def _active_login_row(conn, email: str):
    row = conn.execute(
        """SELECT * FROM login_codes
           WHERE email=? AND consumed_at IS NULL
           ORDER BY created_at DESC LIMIT 1""",
        (email,),
    ).fetchone()
    if not row:
        raise code_expired("no active code")
    try:
        if _parse_dt(row["expires_at"]) < _now():
            conn.execute(
                "UPDATE login_codes SET consumed_at=? WHERE id=?",
                (_now().isoformat(), row["id"]),
            )
            conn.commit()
            raise code_expired("ttl elapsed")
    except AppError:
        raise
    except (TypeError, ValueError) as exc:
        raise code_expired("bad expiry") from exc
    return row


def complete_email_otp(email: str, code: str, user_agent: str = "") -> dict:
    """Consume a valid code and create session, pending-2fa, or profile ticket in one transaction."""
    code = code.strip()
    if not re.fullmatch(r"\d{6}", code):
        raise code_invalid(OTP_MAX_ATTEMPTS, "malformed code")
    conn = db.connect()
    try:
        row = _active_login_row(conn, email)
        attempts = int(row["attempts"] or 0)
        if attempts >= OTP_MAX_ATTEMPTS:
            raise too_many_attempts("max attempts")
        if not hmac.compare_digest(row["code_hash"], hash_login_code(code)):
            nxt = attempts + 1
            conn.execute("UPDATE login_codes SET attempts=? WHERE id=?", (nxt, row["id"]))
            conn.commit()
            if nxt >= OTP_MAX_ATTEMPTS:
                raise too_many_attempts("attempts exhausted")
            raise code_invalid(OTP_MAX_ATTEMPTS - nxt, "mismatch")
        now = _now().isoformat()
        conn.execute("UPDATE login_codes SET consumed_at=? WHERE id=?", (now, row["id"]))
        user_row = conn.execute("SELECT * FROM users WHERE lower(email)=?", (email,)).fetchone()
        if user_row:
            from .totp import totp_enabled

            user = db.user_to_dict(user_row)
            if totp_enabled(user["id"], conn):
                raw = mint_opaque_token()
                conn.execute("DELETE FROM pending_2fa WHERE user_id=?", (user["id"],))
                conn.execute(
                    "INSERT INTO pending_2fa (token_hash, user_id, expires_at) VALUES (?,?,?)",
                    (
                        hash_token(raw),
                        user["id"],
                        (_now() + timedelta(minutes=PENDING_TTL_MIN)).isoformat(),
                    ),
                )
                conn.commit()
                return {"kind": "totp", "raw": raw, "user": user}
            raw = mint_opaque_token()
            created = _now()
            conn.execute(
                """INSERT INTO auth_sessions
                   (id, token_hash, user_id, expires_at, last_seen_at, user_agent, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()),
                    hash_token(raw),
                    user["id"],
                    (created + timedelta(days=SESSION_DAYS)).isoformat(),
                    created.isoformat(),
                    (user_agent or "")[:240],
                    created.isoformat(),
                ),
            )
            conn.commit()
            return {"kind": "session", "raw": raw, "user": user}
        ticket = secrets.token_urlsafe(24)
        conn.execute("DELETE FROM otp_tickets WHERE email=?", (email,))
        conn.execute(
            "INSERT INTO otp_tickets (ticket, email, expires_at) VALUES (?,?,?)",
            (ticket, email, (_now() + timedelta(minutes=TICKET_TTL_MIN)).isoformat()),
        )
        conn.commit()
        return {"kind": "ticket", "ticket": ticket}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_otp_ticket(email: str) -> str:
    ticket = secrets.token_urlsafe(24)
    expires = (_now() + timedelta(minutes=TICKET_TTL_MIN)).isoformat()
    conn = db.connect()
    conn.execute("DELETE FROM otp_tickets WHERE email=?", (email,))
    conn.execute(
        "INSERT INTO otp_tickets (ticket, email, expires_at) VALUES (?,?,?)",
        (ticket, email, expires),
    )
    conn.commit()
    conn.close()
    return ticket


def consume_otp_ticket(ticket: str) -> str:
    conn = db.connect()
    row = conn.execute("SELECT * FROM otp_tickets WHERE ticket=?", (ticket,)).fetchone()
    if not row:
        conn.close()
        raise code_expired("ticket missing")
    try:
        if _parse_dt(row["expires_at"]) < _now():
            conn.execute("DELETE FROM otp_tickets WHERE ticket=?", (ticket,))
            conn.commit()
            conn.close()
            raise code_expired("ticket ttl")
    except AppError:
        raise
    except (TypeError, ValueError) as exc:
        conn.close()
        raise code_expired("ticket bad expiry") from exc
    email = row["email"]
    conn.execute("DELETE FROM otp_tickets WHERE ticket=?", (ticket,))
    conn.commit()
    conn.close()
    return email


def find_user_by_email(email: str) -> dict | None:
    conn = db.connect()
    row = conn.execute("SELECT * FROM users WHERE lower(email)=?", (email,)).fetchone()
    conn.close()
    return db.user_to_dict(row) if row else None


def find_user_by_id(user_id: str) -> dict | None:
    conn = db.connect()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return db.user_to_dict(row) if row else None
