from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import market_cache, market_poller
from app.api.routes.health import router as health_router
from app.api.routes.market_stream import router as market_stream_router
from app.api.routes.markets import router as markets_router
from app.api.routes.social import router as social_router
from app.api.routes.sentiment import router as sentiment_router
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await market_poller.start()
    try:
        yield
    finally:
        await market_poller.stop()
        await market_cache.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(markets_router, prefix="/api")
app.include_router(social_router, prefix="/api")
app.include_router(sentiment_router, prefix="/api")
app.include_router(market_stream_router, prefix="/ws")
