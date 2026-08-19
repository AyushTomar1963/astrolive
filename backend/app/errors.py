from __future__ import annotations

import logging
import os
import uuid
from contextvars import ContextVar

from fastapi.responses import JSONResponse

GENERIC = "Something went wrong on our end. Try again."
INVALID_EMAIL = "Enter a valid email address."
EMAIL_SEND_FAILED = "We couldn't send the code right now. Try again in a minute."
CODE_EXPIRED = "That code expired. Request a new one."
TOO_MANY_ATTEMPTS = "Too many wrong codes. Request a new one."

_LEAK = ("env", ".env", "gmail_", "nodemailer", "smtp")
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
log = logging.getLogger("astrolive")


def is_production() -> bool:
    return os.environ.get("NODE_ENV", "").strip().lower() == "production"


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def leaky(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in _LEAK)


def rate_limited_message(minutes: int) -> str:
    n = max(1, int(minutes))
    return f"Too many requests. Try again in {n} minutes."


def code_invalid_message(left: int) -> str:
    n = max(0, int(left))
    return f"That code isn't right. {n} attempts left."


def safe_user_message(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned or leaky(cleaned):
        return GENERIC
    return cleaned


class AppError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        user_message: str,
        dev_detail: str = "",
    ) -> None:
        self.status = status
        self.code = code
        self.user_message = safe_user_message(user_message)
        self.dev_detail = dev_detail
        super().__init__(self.user_message)


def email_send_failed(dev_detail: str = "") -> AppError:
    return AppError(503, "EMAIL_SEND_FAILED", EMAIL_SEND_FAILED, dev_detail)


def rate_limited(minutes: int, dev_detail: str = "") -> AppError:
    return AppError(429, "RATE_LIMITED", rate_limited_message(minutes), dev_detail)


def code_expired(dev_detail: str = "") -> AppError:
    return AppError(401, "CODE_EXPIRED", CODE_EXPIRED, dev_detail)


def code_invalid(left: int, dev_detail: str = "") -> AppError:
    return AppError(401, "CODE_INVALID", code_invalid_message(left), dev_detail)


def too_many_attempts(dev_detail: str = "") -> AppError:
    return AppError(401, "TOO_MANY_ATTEMPTS", TOO_MANY_ATTEMPTS, dev_detail)


def invalid_email(dev_detail: str = "") -> AppError:
    return AppError(422, "INVALID_EMAIL", INVALID_EMAIL, dev_detail)


def error_payload(
    code: str,
    user_message: str,
    *,
    request_id: str = "",
    dev_detail: str = "",
) -> dict:
    rid = request_id or request_id_var.get()
    body: dict = {
        "ok": False,
        "error": {
            "code": code,
            "userMessage": safe_user_message(user_message),
            "requestId": rid,
        },
    }
    if not is_production() and dev_detail:
        body["error"]["devDetail"] = str(dev_detail)
    return body


def json_error(
    status: int,
    code: str,
    user_message: str,
    *,
    dev_detail: str = "",
) -> JSONResponse:
    rid = request_id_var.get()
    payload = error_payload(code, user_message, request_id=rid, dev_detail=dev_detail)
    log.warning("request=%s code=%s status=%s detail=%s", rid, code, status, dev_detail or user_message)
    return JSONResponse(status_code=status, content=payload, headers={"X-Request-Id": rid})


def from_app_error(exc: AppError) -> JSONResponse:
    return json_error(exc.status, exc.code, exc.user_message, dev_detail=exc.dev_detail)
