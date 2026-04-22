"""
Recommendations router.

GET /recommendations
    - Requires a valid Firebase ID token (Authorization: Bearer <token>)
    - Fetches the authenticated user's preferences from Firestore
    - Returns the 10 nearest item IDs from the in-memory index
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from src.dependencies import get_current_user
from src.ml.nearest_neighbor import NearestNeighborIndex
from src.services.user_vectors import get_user_vector

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# Default number of recommendations to return
DEFAULT_K = 10


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class RecommendationResponse(BaseModel):
    """Ordered list of recommended item IDs."""

    item_ids: list[str]
    user_uid: str


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get("", response_model=RecommendationResponse)
async def get_recommendations(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RecommendationResponse:
    """
    Return the 10 nearest items for the authenticated user's preferences.

    Fetches the user's preferences from Firestore, builds a 14-dimensional vector
    (filling missing categories with 0.5), and queries the ML index.

    The ML index is loaded once at startup and stored in `app.state.nn_index`.
    """
    index: NearestNeighborIndex | None = getattr(request.app.state, "nn_index", None)

    if index is None or not index.is_fitted:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation index is not ready yet.",
        )

    # Fetch user's preference vector from Firestore
    user_vector = await get_user_vector(request.app.state.db, current_user["uid"])

    # Query the index for the DEFAULT_K nearest items
    item_ids = index.query(user_vector, k=DEFAULT_K)

    return RecommendationResponse(
        item_ids=item_ids,
        user_uid=current_user["uid"],
    )
