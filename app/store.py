"""SQLite for the two things that are NOT vectors: users and the audit log.
(Production: swap for Postgres + your IdP/SSO; the interface stays the same.)"""
import hashlib
import hmac
import json
import os
import sqlite3
import time
from pathlib import Path


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000).hex()


class Store:
    def __init__(self, path: Path):
        self.path = str(path)
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, salt TEXT, pw_hash TEXT, role TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, "
                      "username TEXT, role TEXT, event TEXT, detail TEXT)")

    def _conn(self):
        return sqlite3.connect(self.path)

    # ---- users -------------------------------------------------------
    def create_user(self, username: str, password: str, role: str) -> None:
        salt = os.urandom(16)
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?)",
                      (username, salt.hex(), hash_password(password, salt), role))

    def verify_user(self, username: str, password: str) -> str | None:
        """Return the user's role if credentials are valid, else None."""
        with self._conn() as c:
            row = c.execute("SELECT salt, pw_hash, role FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            return None
        candidate = hash_password(password, bytes.fromhex(row[0]))
        return row[2] if hmac.compare_digest(candidate, row[1]) else None

    def get_role(self, username: str) -> str | None:
        with self._conn() as c:
            row = c.execute("SELECT role FROM users WHERE username=?", (username,)).fetchone()
        return row[0] if row else None

    # ---- audit -------------------------------------------------------
    def log(self, username: str, role: str, event: str, detail: dict) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO audit(ts, username, role, event, detail) VALUES (?,?,?,?,?)",
                      (time.time(), username, role, event, json.dumps(detail)))

    def recent_audit(self, limit: int = 50) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT ts, username, role, event, detail FROM audit ORDER BY id DESC LIMIT ?",
                             (limit,)).fetchall()
        return [{"ts": r[0], "username": r[1], "role": r[2], "event": r[3], "detail": json.loads(r[4])} for r in rows]
