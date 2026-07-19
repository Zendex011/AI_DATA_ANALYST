"""
Password hashing and JWT handling.

Uses the `bcrypt` package directly rather than passlib. passlib's bcrypt
backend has a known compatibility break with bcrypt>=4.1 (it calls an
attribute bcrypt removed), which causes confusing crashes on a fresh
install depending on exactly which version pip resolves. Calling bcrypt
directly sidesteps that entirely -- one less moving part to break.
"""

from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt, JWTError
from app.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes if expires_minutes is not None else JWT_EXPIRE_MINUTES
    )
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


class TokenError(Exception):
    pass


def decode_access_token(token: str) -> str:
    """Returns the user_id ("sub" claim). Raises TokenError if invalid/expired."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise TokenError(str(e))

    user_id = payload.get("sub")
    if not user_id:
        raise TokenError("Token has no subject")
    return user_id