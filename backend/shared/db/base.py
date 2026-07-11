from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from sqlalchemy import DateTime, func


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """
    混入类：需要 created_at 和 updated_at 的继承
    使用 server_default 而非 default 防止时间偏差因为 default 是服务器生成时间，而 server_default 是数据库生成时间
    使用 onupdate=func.now() 来实现 updated_at 的自动更新
    """
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )