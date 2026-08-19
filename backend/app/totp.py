from __future__ import annotations

import base64
import hashlib
import hmac
import io
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

import pyotp
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import db
from .auth import (
    SESSION_DAYS,
    hash_token,
    mint_opaque_token,
    otp_pepper,
)
from .errors import AppError, GENERIC, is_production, rate_limited

ISSUER = "AstroLive"
MAX_FAILS = 5
LOCK_MIN = 15
WINDOW = 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _totp_key() -> bytes:
    from .auth import _env_secret

    hexkey = _env_secret("TOTP_KEY", 32)
    try:
        key = bytes.fromhex(hexkey)
    except ValueError as exc:
        raise AppError(500, "ERROR", GENERIC, "bad totp key") from exc
    if len(key) != 32:
        if is_production():
            raise AppError(500, "ERROR", GENERIC, "totp key length")
        key = hashlib.sha256(hexkey.encode()).digest()
    return key


def encrypt_secret(plain: str) -> str:
    aes = AESGCM(_totp_key())
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plain.encode("utf-8"), None)
    return (nonce + ct).hex()


def decrypt_secret(blob: str) -> str:
    raw = bytes.fromhex(blob)
    nonce, ct = raw[:12], raw[12:]
    return AESGCM(_totp_key()).decrypt(nonce, ct, None).decode("utf-8")


def qr_data_url(payload: str) -> str:
    import qrcode
    from qrcode.image.svg import SvgPathImage

    img = qrcode.make(payload, image_factory=SvgPathImage, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _row(user_id: str, conn: sqlite3.Connection | None = None):
    own = conn is None
    if own:
        conn = db.connect()
    row = conn.execute("SELECT * FROM user_totp WHERE user_id=?", (user_id,)).fetchone()
    if own:
        conn.close()
    return row


def totp_enabled(user_id: str, conn: sqlite3.Connection | None = None) -> bool:
    row = _row(user_id, conn)
    return bool(row and int(row["enabled"] or 0) == 1 and row["secret_enc"])


def status(user_id: str) -> dict:
    return {"enabled": totp_enabled(user_id)}


def setup(user_id: str, email: str) -> dict:
    if totp_enabled(user_id):
        raise AppError(409, "INVALID", "Authenticator is already on this account.", "totp on")
    secret = pyotp.random_base32(length=32)
    uri = pyotp.TOTP(secret, digits=6, interval=30, digest=hashlib.sha1).provisioning_uri(
        name=email or user_id,
        issuer_name=ISSUER,
    )
    enc = encrypt_secret(secret)
    conn = db.connect()
    conn.execute(
        """INSERT INTO user_totp (user_id, secret_enc, pending_secret_enc, enabled, fail_count)
           VALUES (?, '', ?, 0, 0)
           ON CONFLICT(user_id) DO UPDATE SET
             pending_secret_enc=excluded.pending_secret_enc,
             fail_count=0,
             locked_until=NULL""",
        (user_id, enc),
    )
    conn.commit()
    conn.close()
    return {"uri": uri, "secret": secret, "qr": qr_data_url(uri)}


def _locked(row) -> None:
    until = row["locked_until"] if row else None
    if not until:
        return
    try:
        lock = _parse_dt(until)
    except (TypeError, ValueError):
        return
    if lock > _now():
        raise rate_limited(max(1, int((lock - _now()).total_seconds() // 60) or 1), "totp lock")


def _record_fail(user_id: str, row) -> None:
    conn = db.connect()
    fails = int((row["fail_count"] if row else 0) or 0) + 1
    locked = None
    if fails >= MAX_FAILS:
        locked = (_now() + timedelta(minutes=LOCK_MIN)).isoformat()
        fails = 0
    conn.execute(
        """INSERT INTO user_totp (user_id, secret_enc, pending_secret_enc, enabled, fail_count, locked_until)
           VALUES (?, '', '', 0, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET fail_count=?, locked_until=?""",
        (user_id, fails, locked, fails, locked),
    )
    conn.commit()
    conn.close()
    if locked:
        raise rate_limited(LOCK_MIN, "totp lock after fails")
    raise AppError(401, "CODE_INVALID", f"That code isn't right. {MAX_FAILS - fails} attempts left.", "totp mismatch")


def _match_totp(secret: str, code: str, last_step: int | None) -> int:
    totp = pyotp.TOTP(secret, digits=6, interval=30, digest=hashlib.sha1)
    now = _now().timestamp()
    for offset in range(-WINDOW, WINDOW + 1):
        for_time = now + offset * 30
        if totp.verify(code, for_time=for_time, valid_window=0):
            step = int(for_time // 30)
            if last_step is not None and step == int(last_step):
                raise AppError(401, "CODE_INVALID", "That code isn't right. 5 attempts left.", "totp replay")
            return step
    raise AppError(401, "CODE_INVALID", "That code isn't right. 5 attempts left.", "totp no match")


def enable(user_id: str, code: str) -> list[str]:
    code = code.strip().replace(" ", "")
    row = _row(user_id)
    if not row or not row["pending_secret_enc"]:
        raise AppError(400, "INVALID", "Start authenticator setup first.", "no pending secret")
    if totp_enabled(user_id):
        raise AppError(409, "INVALID", "Authenticator is already on this account.", "totp on")
    _locked(row)
    secret = decrypt_secret(row["pending_secret_enc"])
    try:
        step = _match_totp(secret, code, None)
    except AppError:
        _record_fail(user_id, row)
        raise
    codes = _mint_recovery(user_id)
    conn = db.connect()
    conn.execute(
        """UPDATE user_totp
           SET secret_enc=?, pending_secret_enc='', enabled=1, last_step=?, fail_count=0, locked_until=NULL
           WHERE user_id=?""",
        (row["pending_secret_enc"], step, user_id),
    )
    conn.commit()
    conn.close()
    return codes


def _hash_recovery(user_id: str, code: str) -> str:
    payload = f"{user_id}:{code.upper()}".encode("utf-8")
    return hmac.new(otp_pepper(), payload, hashlib.sha256).hexdigest()


def _mint_recovery(user_id: str) -> list[str]:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    raw_codes = ["".join(secrets.choice(alphabet) for _ in range(8)) for _ in range(10)]
    conn = db.connect()
    conn.execute("DELETE FROM recovery_codes WHERE user_id=?", (user_id,))
    for code in raw_codes:
        conn.execute(
            "INSERT INTO recovery_codes (id, user_id, code_hash, used_at) VALUES (?,?,?,NULL)",
            (str(uuid.uuid4()), user_id, _hash_recovery(user_id, code)),
        )
    conn.commit()
    conn.close()
    return [f"{c[:4]}-{c[4:]}" for c in raw_codes]


def _consume_recovery(user_id: str, code: str) -> bool:
    cleaned = code.strip().replace("-", "").replace(" ", "").upper()
    if len(cleaned) != 8:
        return False
    want = _hash_recovery(user_id, cleaned)
    conn = db.connect()
    rows = conn.execute(
        "SELECT id, code_hash FROM recovery_codes WHERE user_id=? AND used_at IS NULL",
        (user_id,),
    ).fetchall()
    hit = None
    for row in rows:
        if hmac.compare_digest(row["code_hash"], want):
            hit = row["id"]
            break
    if not hit:
        conn.close()
        return False
    conn.execute("UPDATE recovery_codes SET used_at=? WHERE id=?", (_now().isoformat(), hit))
    conn.commit()
    conn.close()
    return True


def verify_login(user_id: str, code: str) -> str:
    """Consume pending-2fa context caller-side. Returns new session token."""
    row = _row(user_id)
    if not totp_enabled(user_id):
        raise AppError(400, "INVALID", "Authenticator is not on this account.", "totp off")
    _locked(row)
    cleaned = code.strip().replace(" ", "")
    if "-" in cleaned or (cleaned.isalnum() and len(cleaned.replace("-", "")) == 8 and not cleaned.isdigit()):
        if _consume_recovery(user_id, cleaned):
            return _new_session(user_id)
        _record_fail(user_id, row)
    digits = cleaned.replace("-", "")
    if not digits.isdigit() or len(digits) != 6:
        _record_fail(user_id, row)
    secret = decrypt_secret(row["secret_enc"])
    try:
        step = _match_totp(secret, digits, row["last_step"])
    except AppError:
        _record_fail(user_id, row)
        raise
    conn = db.connect()
    conn.execute(
        "UPDATE user_totp SET last_step=?, fail_count=0, locked_until=NULL WHERE user_id=?",
        (step, user_id),
    )
    conn.commit()
    conn.close()
    return _new_session(user_id)


def disable(user_id: str, code: str) -> None:
    if not totp_enabled(user_id):
        raise AppError(400, "INVALID", "Authenticator is not on this account.", "totp off")
    row = _row(user_id)
    _locked(row)
    cleaned = code.strip().replace(" ", "")
    ok = False
    if not cleaned.isdigit():
        ok = _consume_recovery(user_id, cleaned)
    if not ok:
        secret = decrypt_secret(row["secret_enc"])
        try:
            _match_totp(secret, cleaned, row["last_step"])
            ok = True
        except AppError:
            ok = False
    if not ok:
        _record_fail(user_id, row)
    conn = db.connect()
    conn.execute(
        """UPDATE user_totp
           SET enabled=0, secret_enc='', pending_secret_enc='', last_step=NULL, fail_count=0, locked_until=NULL
           WHERE user_id=?""",
        (user_id,),
    )
    conn.execute("DELETE FROM recovery_codes WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def _new_session(user_id: str) -> str:
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
            "",
            now.isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return raw
