import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from .config import settings
from .db import get_db

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False


def issue_session(user_id: str) -> str:
    token = secrets.token_urlsafe(36)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_days)
    get_db().sessions.insert_one({"token_hash": token_hash, "user_id": user_id, "expires_at": expires_at})
    return token


def user_for_token(token: str) -> dict | None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    session = get_db().sessions.find_one({"token_hash": token_hash})
    if not session:
        return None
    user = get_db().users.find_one({"_id": session["user_id"]})
    if user:
        user.pop("password_hash", None)
    return user
