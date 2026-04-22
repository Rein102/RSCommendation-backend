"""
Recommendations router.

GET /recommendations
    - Requires a valid Firebase ID token (Authorization: Bearer <token>)
    - Reads the authenticated user's preferences from Firestore
    - Returns the k nearest activity IDs, re-ranked by category preference
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.dependencies import get_current_user
from src.ml.nearest_neighbor import NearestNeighborIndex
from src.models.recommendations import RecommendationResponse
from src.services.recommendations import get_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationResponse)
async def recommendations(
    request: Request,
    k: int = Query(default=10, ge=1, le=50, description="Number of recommendations to return."),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RecommendationResponse:
    """
    Return the k best-matching activities for the authenticated user.

    Preferences are read from `users/{uid}` in Firestore:
    - `preferences.features`   — 14-dim feature vector for NN lookup
    - `preferences.categories` — 10-dim category preference for re-ranking

    The ML index is built once at startup from the `activities` collection.
    """
    index: NearestNeighborIndex | None = getattr(request.app.state, "nn_index", None)

    if index is None or not index.is_fitted:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation index is not ready yet.",
        )

    activity_categories: dict[str, str] = getattr(
        request.app.state, "activity_categories", {}
    )

    item_ids = await get_recommendations(
        uid=current_user["uid"],
        k=k,
        db=request.app.state.db,
        nn_index=index,
        activity_categories=activity_categories,
    )

    return RecommendationResponse(item_ids=item_ids)
