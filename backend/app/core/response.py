"""统一 API 响应格式"""
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """标准 API 响应格式"""
    code: int = Field(default=0, description="业务状态码，0 表示成功")
    message: str = Field(default="success", description="业务消息")
    data: T | None = Field(default=None, description="响应数据")
    request_id: str = Field(default_factory=lambda: str(uuid4()), description="请求唯一标识")


def success_response(data: Any = None, message: str = "success") -> dict:
    """成功响应快捷函数"""
    return ApiResponse(code=0, message=message, data=data).model_dump()


def error_response(code: int, message: str, data: Any = None) -> dict:
    """错误响应快捷函数"""
    return ApiResponse(code=code, message=message, data=data).model_dump()
