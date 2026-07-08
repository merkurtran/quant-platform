from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User


class EmailAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass

def register_user(db: Session, email: str, password: str, nickname: str) -> User:
    # 先快速检查，但最终由数据库唯一约束兜底
    if db.query(User).filter(User.email == email).first():
        raise EmailAlreadyExistsError("Email already exists")
    hashed_password = hash_password(password)
    user = User(email=email, password_hash=hashed_password, nickname=nickname)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise EmailAlreadyExistsError("Email already exists")


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        # 用户不存在时也执行一次密码验证（使用硬编码假哈希），
        # 消除"用户不存在 vs 密码错误"之间的时序侧信道差异。
        # 假哈希来源于 bcrypt 对 "no_user_dummy" 的哈希，只取一次计算时间。
        verify_password(password, "$2b$12$LJ3m4ys3GZ0Z5qF9qJx3BOp0h8qIzK5kfZgYIZ9E6AtJ4RXpRC5Ay")
        raise InvalidCredentialsError("Invalid credentials")
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid credentials")
    return user


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise UserNotFoundError(f"User {user_id} not found")
    return user