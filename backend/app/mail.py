from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage

from .errors import AppError, email_send_failed, is_production
from .gemini import load_env

log = logging.getLogger("astrolive")
_WARNED = False


def _smtp_blocked() -> bool:
    """Render (and similar PaaS) block outbound SMTP 25/465/587."""
    return bool(
        os.environ.get("RENDER", "").strip()
        or os.environ.get("RENDER_SERVICE_ID", "").strip()
        or is_production()
    )


def send_email(*, to: str, subject: str, html: str, text: str) -> None:
    """Single outbound mail interface. Swap the production provider here only."""
    load_env()
    if _smtp_blocked():
        if os.environ.get("RESEND_API_KEY", "").strip():
            _resend_transport(to=to, subject=subject, html=html, text=text)
            return
        raise email_send_failed("resend key missing")

    _console_transport(to=to, subject=subject, text=text)
    user, password = _gmail_creds()
    if user and password:
        _gmail_transport(to=to, subject=subject, html=html, text=text)


def _console_transport(*, to: str, subject: str, text: str) -> None:
    print(f"\n--- email (console) to {to} ---\n{subject}\n{text}\n--- end email ---\n", flush=True)


def _gmail_creds() -> tuple[str, str]:
    load_env()
    user = os.environ.get("GMAIL_USER", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if user and password:
        return user, password
    return "", ""


def _gmail_transport(*, to: str, subject: str, html: str, text: str) -> None:
    user, password = _gmail_creds()
    if not user or not password:
        raise email_send_failed("mail creds missing")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"AstroLive <{user}>"
    msg["To"] = to
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
            smtp.starttls(context=ctx)
            smtp.login(user, password)
            smtp.send_message(msg)
    except Exception as exc:  # noqa: BLE001
        log.exception("mail send failed")
        raise email_send_failed(str(exc)) from exc


def _resend_transport(*, to: str, subject: str, html: str, text: str) -> None:
    key = os.environ.get("RESEND_API_KEY", "").strip()
    sender = os.environ.get("RESEND_FROM", "").strip() or "AstroLive <onboarding@resend.dev>"
    if not key:
        raise email_send_failed("resend key missing")
    payload = json.dumps(
        {"from": sender, "to": [to], "subject": subject, "html": html, "text": text}
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AstroLive/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status >= 300:
                raise email_send_failed(f"resend status {resp.status}")
    except AppError:
        raise
    except urllib.error.HTTPError as exc:
        detail = _http_error_detail(exc)
        log.exception("resend http error")
        raise email_send_failed(detail) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("resend send failed")
        raise email_send_failed(str(exc)) from exc


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    body = ""
    try:
        body = exc.read().decode("utf-8", "replace")[:400]
    except Exception:  # noqa: BLE001
        body = ""
    return f"resend {exc.code} {body}".strip()


def otp_email_content(code: str) -> tuple[str, str, str]:
    subject = "Your AstroLive sign-in code"
    text = (
        f"Your AstroLive sign-in code is {code}.\n"
        "This code expires in 10 minutes.\n\n"
        "If you didn't request this, ignore this email.\n"
    )
    html = f"""<!DOCTYPE html>
<html><body style="font-family:Georgia,serif;background:#0b0711;color:#f4eff8;padding:24px;">
  <p>Your AstroLive sign-in code is</p>
  <p style="font-family:ui-monospace,Menlo,Consolas,monospace;font-size:32px;letter-spacing:0.18em;color:#e9ce8e;">{code}</p>
  <p>This code expires in 10 minutes.</p>
  <p style="color:#b0a3c6;font-size:14px;">If you didn't request this, ignore this email.</p>
</body></html>"""
    return subject, html, text


def send_otp(to_email: str, code: str) -> None:
    subject, html, text = otp_email_content(code)
    send_email(to=to_email, subject=subject, html=html, text=text)


def warn_if_unconfigured() -> None:
    global _WARNED
    if _WARNED:
        return
    _WARNED = True
    load_env()
    gmail = bool(_gmail_creds()[0])
    resend = bool(os.environ.get("RESEND_API_KEY", "").strip())
    if _smtp_blocked() and not resend:
        log.warning(
            "\n============================================================\n"
            "Render cannot send Gmail SMTP (port 587 is blocked).\n"
            "Set RESEND_API_KEY (and optional RESEND_FROM) on this service.\n"
            "============================================================\n"
        )
    elif _smtp_blocked() and resend:
        log.info("Mail transport: Resend HTTPS.")
    elif gmail:
        log.info("Mail transport: Gmail SMTP (inbox delivery on).")
    else:
        log.info(
            "Mail transport: console only. Codes will not reach an inbox until "
            "GMAIL_USER and GMAIL_APP_PASSWORD are set in backend/.env "
            "(Google Account > Security > 2-Step Verification > App passwords)."
        )
