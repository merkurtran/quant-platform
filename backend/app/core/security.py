from datetime import datetime, timedelta, timezone
import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


settings = get_settings()

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt.secret_key.get_secret_value(), algorithm=settings.jwt.algorithm)


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.jwt.secret_key.get_secret_value(), algorithms=[settings.jwt.algorithm])
    if payload.get("type") == "refresh":
        raise JWTError("This is a refresh token, not an access token")
    return payload


def decode_refresh_token(token: str) -> dict:
    payload = jwt.decode(token, settings.jwt.secret_key.get_secret_value(), algorithms=[settings.jwt.algorithm])
    if payload.get("type") != "refresh":
        raise JWTError("This is not a refresh token")
    return payload


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt.refresh_token_expire_days)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.jwt.secret_key.get_secret_value(), algorithm=settings.jwt.algorithm)