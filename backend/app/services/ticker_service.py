from app.models.market import CreateTrackedTickerRequest, TrackedTicker
from app.repositories.ticker_repository import TickerRepository


class TickerService:
    def __init__(self, repository: TickerRepository) -> None:
        self.repository = repository

    def list_tickers(self) -> list[TrackedTicker]:
        return self.repository.list_all()

    def add_ticker(self, request: CreateTrackedTickerRequest) -> list[TrackedTicker]:
        ticker = TrackedTicker(
            code=request.code.strip().upper(),
            symbol=request.symbol.strip().upper(),
            name=request.name.strip(),
            provider=request.provider.strip().lower(),
            aliases=[alias.strip() for alias in request.aliases if alias.strip()],
            metadata=request.metadata,
        )
        return self.repository.add(ticker)

    def delete_ticker(self, code: str) -> list[TrackedTicker]:
        return self.repository.delete(code)
