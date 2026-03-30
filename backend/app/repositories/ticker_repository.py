import json
from pathlib import Path

from app.models.market import TrackedTicker


class TickerRepository:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write(
                [
                    TrackedTicker(code="CL", symbol="CL=F", name="Crude Oil Futures"),
                    TrackedTicker(code="GC=F", symbol="GC=F", name="Gold Futures"),
                ]
            )

    def list_all(self) -> list[TrackedTicker]:
        payload = json.loads(self.file_path.read_text(encoding="utf-8"))
        return [TrackedTicker(**item) for item in payload]

    def add(self, ticker: TrackedTicker) -> list[TrackedTicker]:
        tickers = self.list_all()
        normalized = ticker.code.upper()
        if any(existing.code.upper() == normalized for existing in tickers):
            raise ValueError(f"Ticker code '{ticker.code}' already exists.")
        tickers.append(ticker)
        self._write(tickers)
        return tickers

    def delete(self, code: str) -> list[TrackedTicker]:
        tickers = self.list_all()
        filtered = [ticker for ticker in tickers if ticker.code.upper() != code.upper()]
        if len(filtered) == len(tickers):
            raise ValueError(f"Ticker code '{code}' was not found.")
        self._write(filtered)
        return filtered

    def _write(self, tickers: list[TrackedTicker]) -> None:
        payload = [ticker.model_dump(mode="json") for ticker in tickers]
        self.file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
