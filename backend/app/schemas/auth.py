from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    nickname: str = Field(min_length=1, max_length=16)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    """对外暴露的用户信息"""
    id: int
    email: EmailStr
    nickname: str
    model_config = {"from_attributes": True} # 允许从 SQLAlchemy 的User对象转换


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: UserPublic


class RefreshTokenRequest(BaseModel):
    refresh_token: str