import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Header
from jose import JWTError
from starlette.websockets import WebSocketState

from app.core.security import decode_access_token
from shared.logging_config import get_logger
from shared.redis_client import get_async_redis_client

logger = get_logger("ws.market")

router = APIRouter()


@router.websocket("/ws/market")
async def market_ws(
    websocket: WebSocket,
    token: str | None = Query(None),
    authorization: str | None = Header(None, alias="authorization"),
):
    """行情 + 告警统一 WebSocket 端点。

    支持两种消息类型：
      - 行情：客户端发送 {"action": "subscribe", "symbols": ["600519.SH"]} 订阅个股行情
      - 告警：连接建立后自动订阅该用户的告警频道 alerts:{user_id}
    """
    # token 优先从 Authorization 头提取，其次从 query 参数（向后兼容）
    t = None
    if authorization and authorization.startswith("Bearer "):
        t = authorization.removeprefix("Bearer ")
    elif token:
        t = token

    if not t:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        payload = decode_access_token(t)
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    await websocket.accept()
    logger.info(f"WebSocket market connection established for user {user_id}")
    redis = get_async_redis_client()
    pubsub = redis.pubsub()
    subscribed_quotes = set()

    # 连接后立即订阅该用户的告警频道
    alert_channel = f"alerts:{user_id}"
    await pubsub.subscribe(alert_channel)

    async def receive_subscriptions():
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json({"event": "error", "message": "Invalid JSON"})
                continue

            if data.get("action") == "subscribe":
                symbols = data.get("symbols") or []
                for symbol in symbols:
                    if symbol not in subscribed_quotes:
                        await pubsub.subscribe(f"quotes:{symbol}")
                        subscribed_quotes.add(symbol)
                        cached = await redis.get(f"latest_price:{symbol}")
                        if cached and websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.send_text(cached)

    async def forward_messages():
        async for message in pubsub.listen():
            if message.get("type") == "message":
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message.get("data"))

    try:
        await asyncio.gather(receive_subscriptions(), forward_messages())
    except WebSocketDisconnect:
        logger.info(f"WebSocket market disconnected for user {user_id}")
    finally:
        await pubsub.aclose()
