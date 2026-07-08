from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from contextlib import asynccontextmanager
import asyncio

from app.api.auth import router as auth_router
from app.api.market import router as market_router
from app.core.config import get_settings
from app.core.middleware import ApiResponseMiddleware
from app.ws.market_ws import router as market_ws_router
from shared.db.session import engine
from shared.logging_config import get_logger

logger = get_logger("app.main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """幂等检查 Klines 是否为 TimescaleDB 超表，不是则转换。
    使用 run_sync 避免在事件循环内阻塞。
    覆盖直接建表（绕过迁移脚本）导致 hypertable 遗漏的情况。"""
    def _ensure_hypertable():
        with engine.begin() as conn:
            result = conn.execute(
                text("SELECT EXISTS(SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name='klines')")
            ).scalar()
            if not result:
                conn.execute(text("SELECT create_hypertable('klines', 'ts', if_not_exists => TRUE)"))
                logger.info("Klines 表已转换为 TimescaleDB hypertable")
    try:
        await asyncio.to_thread(_ensure_hypertable)
    except Exception as e:
        logger.warning(f"Hypertable 初始化跳过（可能 TimescaleDB 未安装）: {e}")
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ApiResponseMiddleware)

app.include_router(auth_router)
app.include_router(market_router)
app.include_router(market_ws_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}