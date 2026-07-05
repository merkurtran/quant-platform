from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.core.config import get_settings
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserPublic
from app.services.auth_service import (
    register_user,
    authenticate_user,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
)
from shared.db.session import get_db


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = register_user(db, payload.email, payload.password, payload.nickname)
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    access_token = create_access_token(user.id)
    # TODO: 实现 refresh token 逻辑
    return TokenResponse(access_token=access_token, 
                         refresh_token=access_token, 
                         expires_in=settings.jwt.access_token_expire_minutes * 60, 
                         user=UserPublic.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, payload.email, payload.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(user.id)
    # TODO: 实现 refresh token 逻辑
    return TokenResponse(access_token=access_token, 
                         refresh_token=access_token, 
                         expires_in=settings.jwt.access_token_expire_minutes * 60, 
                         user=UserPublic.model_validate(user))