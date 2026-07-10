from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.exceptions import BizException, BizErrorCode
from app.core.security import decode_access_token
from app.models.user import User
from shared.db.session import get_db
from app.services.auth_service import get_user_by_id, UserNotFoundError

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials 

    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
        if payload.get("type") != "access":
            raise BizException(
                BizErrorCode.UNAUTHORIZED,
                "Invalid token type",
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (JWTError, ValueError, TypeError):
        raise BizException(
            BizErrorCode.UNAUTHORIZED,
            "Could not validate credentials",
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return get_user_by_id(db, user_id)
    except UserNotFoundError:
        raise BizException(
            BizErrorCode.UNAUTHORIZED,
            "User not found",
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )