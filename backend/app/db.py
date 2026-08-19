from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "astrolive.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            dob TEXT NOT NULL,
            tob TEXT NOT NULL,
            place TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            gotra TEXT DEFAULT '',
            wallet INTEGER DEFAULT 180,
            streak INTEGER DEFAULT 6,
            upay_date TEXT DEFAULT '',
            chart_json TEXT NOT NULL,
            email TEXT DEFAULT '',
            password_hash TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS matches (
            token TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            host_id TEXT NOT NULL,
            guest_id TEXT,
            guest_name TEXT,
            result_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(host_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            title TEXT NOT NULL,
            price INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            astrologer_id TEXT NOT NULL DEFAULT 'ak',
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS auth_sessions (
            id TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL UNIQUE,
            user_id TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            user_agent TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS login_codes (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            consumed_at TEXT,
            request_ip TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_login_codes_email ON login_codes(email);
        CREATE INDEX IF NOT EXISTS idx_login_codes_ip ON login_codes(request_ip);
        CREATE TABLE IF NOT EXISTS otp_tickets (
            ticket TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_totp (
            user_id TEXT PRIMARY KEY,
            secret_enc TEXT NOT NULL DEFAULT '',
            pending_secret_enc TEXT NOT NULL DEFAULT '',
            enabled INTEGER NOT NULL DEFAULT 0,
            last_step INTEGER,
            fail_count INTEGER DEFAULT 0,
            locked_until TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS recovery_codes (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            used_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS pending_2fa (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        """
    )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "email" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''")
    if "password_hash" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT ''")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL AND email != ''"
    )
    conn.commit()
    conn.close()


def user_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["chart"] = json.loads(d.pop("chart_json"))
    d.pop("password_hash", None)
    return d
