from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import market_service, provider, ticker_service
from app.models.market import CreateTrackedTickerRequest, MarketSnapshot, TrackedTicker

router = APIRouter(tags=["markets"])


@router.get("/markets", response_model=MarketSnapshot)
async def get_markets() -> MarketSnapshot:
    snapshot = await market_service.get_snapshot()
    if snapshot.updated_at is None:
        snapshot = await market_service.refresh_snapshot()
    return snapshot


@router.get("/providers")
async def get_provider_info() -> dict[str, str]:
    return {"provider": provider.provider_name}


@router.get("/tickers", response_model=list[TrackedTicker])
async def list_tickers() -> list[TrackedTicker]:
    return ticker_service.list_tickers()


@router.post("/tickers", response_model=list[TrackedTicker], status_code=status.HTTP_201_CREATED)
async def add_ticker(request: CreateTrackedTickerRequest) -> list[TrackedTicker]:
    try:
        tickers = ticker_service.add_ticker(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await market_service.refresh_snapshot()
    return tickers


@router.delete("/tickers/{code}", response_model=list[TrackedTicker])
async def delete_ticker(code: str) -> list[TrackedTicker]:
    try:
        tickers = ticker_service.delete_ticker(code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await market_service.refresh_snapshot()
    return tickers
