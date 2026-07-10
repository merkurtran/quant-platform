from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.exceptions import BizException, BizErrorCode
from app.core.security import create_access_token, create_refresh_token, decode_refresh_token
from app.core.config import get_settings
from app.core.rate_limit import rate_limiter
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserPublic, RefreshTokenRequest
from app.services.auth_service import (
    register_user,
    authenticate_user,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    get_user_by_id,
    UserNotFoundError
)
from shared.db.session import get_db


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db), _: None = Depends(rate_limiter(max_requests=5, window_seconds=60))):
    try:
        user = register_user(db, payload.email, payload.password, payload.nickname)
    except EmailAlreadyExistsError:
        raise BizException(BizErrorCode.ALREADY_EXISTS, "Email already exists", status_code=409)
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(access_token=access_token, 
                         refresh_token=refresh_token, 
                         expires_in=settings.jwt.access_token_expire_minutes * 60, 
                         user=UserPublic.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db), _: None = Depends(rate_limiter(max_requests=10, window_seconds=60))):
    try:
        user = authenticate_user(db, payload.email, payload.password)
    except InvalidCredentialsError:
        raise BizException(BizErrorCode.UNAUTHORIZED, "Invalid credentials", status_code=401)
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(access_token=access_token, 
                         refresh_token=refresh_token, 
                         expires_in=settings.jwt.access_token_expire_minutes * 60, 
                         user=UserPublic.model_validate(user))


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db), _: None = Depends(rate_limiter(max_requests=10, window_seconds=60))):
    try:
        token_payload = decode_refresh_token(payload.refresh_token)
    except JWTError:
        raise BizException(
            BizErrorCode.AUTH_TOKEN_EXPIRED,
            "Invalid or expired refresh token",
            status_code=401,
        )

    user_id = int(token_payload.get("sub"))

    try:
        user = get_user_by_id(db, user_id)
    except UserNotFoundError:
        raise BizException(
            BizErrorCode.NOT_FOUND,
            "User not found",
            status_code=401,
        )

    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.jwt.access_token_expire_minutes * 60,
        user=UserPublic.model_validate(user),
    )