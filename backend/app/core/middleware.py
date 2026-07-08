"""统一 API 响应格式中间件"""
import json
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


_UNWRAPPED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class ApiResponseMiddleware(BaseHTTPMiddleware):
    """将所有成功 JSON 响应包装为 {code, message, data, request_id} 格式"""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # 跳过非 2xx 响应（异常已由 FastAPI 的 exception_handler 处理）、
        # 非 JSON 响应、以及不需要包装的路径
        if (
            response.status_code >= 300
            or response.headers.get("content-type") != "application/json"
            or request.url.path in _UNWRAPPED_PATHS
        ):
            return response

        # 读取原始响应体
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        try:
            data = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            # 非 JSON 响应（如文件下载、流）直接透传
            return Response(content=body, status_code=response.status_code, headers=dict(response.headers))

        # 如果已经是包装格式，直接返回原响应（避免二次包装）
        if isinstance(data, dict) and "code" in data and "message" in data and "data" in data:
            return Response(content=body, status_code=response.status_code, headers=dict(response.headers))

        wrapped = {
            "code": 0,
            "message": "success",
            "data": data,
            "request_id": str(uuid4()),
        }

        # 剥离会冲突的 header，让 Starlette 按新 body 重新计算 Content-Length
        safe_headers = {
            k: v for k, v in response.headers.items()
            if k.lower() not in ("content-length", "content-type", "transfer-encoding")
        }
        return Response(
            content=json.dumps(wrapped, ensure_ascii=False),
            status_code=response.status_code,
            headers=safe_headers,
            media_type="application/json",
        )
