from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import fear_greed_service
from app.models.sentiment import FearGreedSnapshot

router = APIRouter(tags=["sentiment"])


@router.get("/sentiment/fear-greed", response_model=FearGreedSnapshot)
async def get_fear_greed_snapshot() -> FearGreedSnapshot:
    try:
        return await fear_greed_service.fetch_snapshot()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch fear and greed index: {exc}",
        ) from exc
