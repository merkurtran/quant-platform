from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.market import router as market_router
from app.core.config import get_settings
from app.ws.market_ws import router as market_ws_router


settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(market_router)
app.include_router(market_ws_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}