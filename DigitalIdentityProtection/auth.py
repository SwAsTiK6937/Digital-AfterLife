"""
Login helpers.

- App passwords are hashed with argon2 (pwdlib). Plain passwords are never stored.
- The session is a signed cookie: "<user_id>|<issued_timestamp>|<HMAC signature>".
  Changing any character breaks the signature, so a user can't pretend to be someone else.
- Simple lockout: 5 wrong passwords for one email within 10 minutes -> blocked for 5 minutes.
"""
import hashlib
import hmac
import os
import secrets
import time

from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from database import BASE_DIR, get_db
from models import User

password_hasher = PasswordHash.recommended()

COOKIE_NAME = "dip_session"
SESSION_SECONDS = 8 * 60 * 60
SECRET_FILE = os.path.join(BASE_DIR, ".secret_key")


def _secret_key() -> bytes:
    """Random key created once and kept in .secret_key (never commit this file)."""
    env = os.environ.get("DIP_SECRET_KEY")
    if env:
        return env.encode()
    if not os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "w") as f:
            f.write(secrets.token_hex(32))
    with open(SECRET_FILE) as f:
        return f.read().strip().encode()


SECRET = _secret_key()


def hash_password(plain: str) -> str:
    return password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return password_hasher.verify(plain, hashed)


def _sign(payload: str) -> str:
    return hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()


def make_session_cookie(user_id: str) -> str:
    payload = f"{user_id}|{int(time.time())}"
    return f"{payload}|{_sign(payload)}"


def read_session_cookie(value: str | None) -> str | None:
    """Return the user_id if the cookie is genuine and not expired, else None."""
    if not value or value.count("|") != 2:
        return None
    user_id, issued, signature = value.split("|")
    if not hmac.compare_digest(_sign(f"{user_id}|{issued}"), signature):
        return None
    if not issued.isdigit() or time.time() - int(issued) > SESSION_SECONDS:
        return None
    return user_id


# ---------------- failed-login lockout (kept in memory) ----------------
_failed: dict[str, list[float]] = {}
MAX_ATTEMPTS, WINDOW, LOCK = 5, 600, 300


def is_locked(email: str) -> bool:
    now = time.time()
    attempts = [t for t in _failed.get(email, []) if now - t < WINDOW]
    _failed[email] = attempts
    return len(attempts) >= MAX_ATTEMPTS and now - attempts[-1] < LOCK


def record_failure(email: str) -> None:
    _failed.setdefault(email, []).append(time.time())


def clear_failures(email: str) -> None:
    _failed.pop(email, None)


# ---------------- FastAPI dependencies ----------------
class LoginRequired(Exception):
    """Raised when there is no valid session; main.py turns it into a redirect to /login."""


class AdminRequired(Exception):
    pass


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = read_session_cookie(request.cookies.get(COOKIE_NAME))
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise LoginRequired()
    return user


def current_member(user: User = Depends(current_user)) -> User:
    """Normal account holder pages. Admins are sent to the admin overview."""
    if user.is_admin:
        raise AdminRequired()
    return user


def current_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=404)  # don't reveal that the admin page exists
    return user
