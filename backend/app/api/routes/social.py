from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import truth_social_service
from app.models.social import SocialFeedResponse

router = APIRouter(tags=["social"])


@router.get("/social/truth", response_model=SocialFeedResponse)
async def get_truth_social_feed(
    limit: int = Query(10, ge=1, le=20),
) -> SocialFeedResponse:
    try:
        return await truth_social_service.get_latest_posts(limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Truth Social feed: {exc}",
        ) from exc
