import json
from datetime import datetime
from typing import Any

from redis.asyncio import Redis

from app.core.config import Settings
from app.models.market import MarketHistoryResponse, MarketQuote


class RedisMarketCache:
    def __init__(self, settings: Settings) -> None:
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)

    async def close(self) -> None:
        await self.client.aclose()

    async def set_latest_quote(self, quote: MarketQuote) -> None:
        payload = {
            "code": quote.code,
            "provider": quote.source,
            "provider_symbol": quote.symbol,
            "price": quote.price,
            "previous_close": quote.previous_close,
            "change": quote.change,
            "change_percent": quote.change_percent,
            "five_min_change": quote.five_min_change,
            "five_min_change_percent": quote.five_min_change_percent,
            "market_state": quote.market_state,
            "timestamp": _metadata_value(quote.metadata, "last_bar_time"),
        }
        await self.client.set(_latest_quote_key(quote.code), json.dumps(payload))

    async def set_prev_5m_close(self, quote: MarketQuote) -> None:
        price = _metadata_value(quote.metadata, "prev_5m_close")
        if price is None:
            return

        payload = {
            "code": quote.code,
            "price": price,
            "bar_closed_at": _metadata_value(quote.metadata, "prev_5m_bar_closed_at"),
            "source_timestamp": _metadata_value(quote.metadata, "last_bar_time"),
        }
        await self.client.set(_prev_5m_key(quote.code), json.dumps(payload))

    async def get_chart_history(self, cache_key: str) -> MarketHistoryResponse | None:
        payload = await self.client.get(_history_key(cache_key))
        if not payload:
            return None
        return MarketHistoryResponse.model_validate_json(payload)

    async def set_chart_history(self, cache_key: str, history: MarketHistoryResponse) -> None:
        await self.client.set(_history_key(cache_key), history.model_dump_json())


def _latest_quote_key(code: str) -> str:
    return f"market:last:{code}"


def _prev_5m_key(code: str) -> str:
    return f"market:ref:5m:prev_close:{code}"


def _history_key(cache_key: str) -> str:
    return f"market:history:{cache_key}"


def _metadata_value(metadata: dict[str, Any], key: str) -> Any:
    value = metadata.get(key)
    if isinstance(value, datetime):
        return value.isoformat()
    return value
