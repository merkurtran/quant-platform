import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User

logger = logging.getLogger(__name__)


class EmailAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass

def register_user(db: Session, email: str, password: str, nickname: str) -> User:
    """
    注册用户：使用 ON CONFLICT (email) DO NOTHING 原子化防重。

    相比先 SELECT 再 INSERT 的 check-then-act 模式，
    INSERT ... ON CONFLICT 在数据库层面保证原子性，消除竞态窗口。
    """
    hashed_password = hash_password(password)

    stmt = (
        pg_insert(User)
        .values(email=email, password_hash=hashed_password, nickname=nickname)
        .on_conflict_do_nothing(constraint_name="uq_users_email")
        .returning(User)
    )
    result = db.execute(stmt).mappings().one_or_none()

    if result is None:
        raise EmailAlreadyExistsError("Email already exists")

    db.commit()
    return result  # type: ignore[return-value]


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