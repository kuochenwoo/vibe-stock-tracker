from app.core.constants import (
    ASSET_TYPE_CRYPTO,
    CRYPTO_SYMBOL_SUFFIXES,
    DEFAULT_SESSION_START_BY_ASSET,
    DEFAULT_SESSION_TIMEZONE_BY_ASSET,
    FUTURES_SYMBOL_SUFFIX,
)
from app.models.market import CreateTrackedTickerRequest, TrackedTicker
from app.repositories.ticker_repository import TickerRepository


class TickerService:
    def __init__(self, repository: TickerRepository) -> None:
        self.repository = repository

    def list_tickers(self) -> list[TrackedTicker]:
        return self.repository.list_all()

    def add_ticker(self, request: CreateTrackedTickerRequest) -> list[TrackedTicker]:
        metadata = dict(request.metadata or {})
        metadata.setdefault("asset_type", _infer_asset_type(request.symbol))
        metadata.setdefault("session_timezone", _default_timezone(metadata["asset_type"]))
        metadata.setdefault("session_start", _default_session_start(metadata["asset_type"]))

        ticker = TrackedTicker(
            code=request.code.strip().upper(),
            symbol=request.symbol.strip().upper(),
            name=request.name.strip(),
            provider=request.provider.strip().lower(),
            aliases=[alias.strip() for alias in request.aliases if alias.strip()],
            metadata=metadata,
        )
        return self.repository.add(ticker)

    def delete_ticker(self, code: str) -> list[TrackedTicker]:
        return self.repository.delete(code)


def _infer_asset_type(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if normalized.endswith(FUTURES_SYMBOL_SUFFIX):
        return "futures"
    if normalized.endswith(CRYPTO_SYMBOL_SUFFIXES):
        return ASSET_TYPE_CRYPTO
    return "stock"


def _default_timezone(asset_type: str) -> str:
    return DEFAULT_SESSION_TIMEZONE_BY_ASSET.get(asset_type, "America/New_York")


def _default_session_start(asset_type: str) -> str:
    return DEFAULT_SESSION_START_BY_ASSET.get(asset_type, "04:00")
