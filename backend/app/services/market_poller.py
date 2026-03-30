import asyncio

from app.services.market_service import MarketService


class MarketPoller:
    def __init__(self, service: MarketService, interval_seconds: int) -> None:
        self.service = service
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def _run(self) -> None:
        while True:
            await self.service.refresh_snapshot()
            await asyncio.sleep(self.interval_seconds)
