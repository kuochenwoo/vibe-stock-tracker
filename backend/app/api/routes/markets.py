from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.dependencies import (
    alert_service,
    get_market_history_use_case,
    get_moving_averages_use_case,
    market_service,
    preferences_service,
    provider,
    ticker_service,
)
from app.models.market import (
    AlertRule,
    CreateTrackedTickerRequest,
    CreateAlertRuleRequest,
    MarketHistoryQuery,
    MovingAverageSnapshot,
    MarketHistoryResponse,
    MarketSnapshot,
    PanelOrderPreference,
    TrackedTicker,
    UpdatePanelOrderPreferenceRequest,
)

router = APIRouter(tags=["markets"])


@router.get("/markets", response_model=MarketSnapshot)
async def get_markets() -> MarketSnapshot:
    snapshot = await market_service.get_snapshot()
    if snapshot.updated_at is None:
        snapshot = await market_service.refresh_snapshot()
    return snapshot


@router.get("/markets/{code}/history", response_model=MarketHistoryResponse)
async def get_market_history(
    code: str,
    query: Annotated[MarketHistoryQuery, Depends()],
) -> MarketHistoryResponse:
    try:
        return await get_market_history_use_case.execute(code, range_value=query.range)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/markets/{code}/moving-averages", response_model=MovingAverageSnapshot)
async def get_market_moving_averages(code: str) -> MovingAverageSnapshot:
    try:
        return await get_moving_averages_use_case.execute(code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/providers")
async def get_provider_info() -> dict[str, str]:
    return {"provider": provider.provider_name}


@router.get("/tickers", response_model=list[TrackedTicker])
async def list_tickers() -> list[TrackedTicker]:
    return ticker_service.list_tickers()


@router.post("/tickers", response_model=list[TrackedTicker], status_code=status.HTTP_201_CREATED)
async def add_ticker(
    request: CreateTrackedTickerRequest,
    background_tasks: BackgroundTasks,
) -> list[TrackedTicker]:
    try:
        tickers = ticker_service.add_ticker(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await market_service.publish_tracked_tickers(tickers)
    background_tasks.add_task(market_service.warm_ticker_data, request.code.strip().upper())
    return tickers


@router.delete("/tickers/{code}", response_model=list[TrackedTicker])
async def delete_ticker(
    code: str,
    background_tasks: BackgroundTasks,
) -> list[TrackedTicker]:
    try:
        tickers = ticker_service.delete_ticker(code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await market_service.publish_tracked_tickers(tickers)
    background_tasks.add_task(market_service.refresh_snapshot)
    return tickers


@router.get("/preferences/panel-order", response_model=PanelOrderPreference)
async def get_panel_order_preference() -> PanelOrderPreference:
    return preferences_service.get_panel_order()


@router.put("/preferences/panel-order", response_model=PanelOrderPreference)
async def update_panel_order_preference(
    request: UpdatePanelOrderPreferenceRequest,
) -> PanelOrderPreference:
    return preferences_service.save_panel_order(request.codes)


@router.get("/alerts", response_model=list[AlertRule])
async def list_alerts() -> list[AlertRule]:
    return alert_service.list_alerts()


@router.post("/alerts", response_model=list[AlertRule], status_code=status.HTTP_201_CREATED)
async def add_alert(request: CreateAlertRuleRequest) -> list[AlertRule]:
    try:
        return alert_service.add_alert(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/alerts/{alert_id}", response_model=list[AlertRule])
async def delete_alert(alert_id: str) -> list[AlertRule]:
    try:
        return alert_service.delete_alert(alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
