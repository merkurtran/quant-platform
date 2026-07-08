import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from shared.redis_client import async_redis_client


router = APIRouter()

@router.websocket("/ws/market")
async def market_ws(websocket: WebSocket):
    await websocket.accept()
    pubsub = async_redis_client.pubsub()
    
    async def receive_subscriptions():
        """负责持续监听客户端发来的订阅请求"""
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if data.get("action") == "subscribe":
                symbols = data.get("symbols") or []
                for symbol in symbols:
                    await pubsub.subscribe(f"quotes:{symbol}")

    async def forward_quotes():
        """负责持续监听 redis 发布的行情数据,并转发给客户端"""
        async for message in pubsub.listen():
            if message.get("type") == "message":
                await websocket.send_text(message.get("data"))

    try:
        await asyncio.gather(receive_subscriptions(), forward_quotes())
    except WebSocketDisconnect:
        print(f"Client disconnected")
    finally:
        await pubsub.close()