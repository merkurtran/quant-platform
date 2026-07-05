from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User


class EmailAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def register_user(db: Session, email: str, password: str, nickname: str) -> User:
    if db.query(User).filter(User.email == email).first():
        raise EmailAlreadyExistsError("Email already exists")
    hashed_password = hash_password(password)
    user = User(email=email, password_hash=hashed_password, nickname=nickname)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise InvalidCredentialsError("Invalid credentials")
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid credentials")
    return user