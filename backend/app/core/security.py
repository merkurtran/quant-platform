from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt

from app.core.config import get_settings


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

settings = get_settings()

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt.secret_key.get_secret_value(), algorithm=settings.jwt.algorithm)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt.secret_key.get_secret_value(), algorithms=[settings.jwt.algorithm])