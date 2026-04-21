"""
Recommendations router.

POST /recommendations
    - Requires a valid Firebase ID token (Authorization: Bearer <token>)
    - Accepts a query vector from the Flutter client
    - Returns the k nearest item IDs from the in-memory index
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.dependencies import get_current_user
from src.ml.nearest_neighbor import NearestNeighborIndex

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class RecommendationRequest(BaseModel):
    """Query vector sent by the Flutter client."""

    vector: list[float] = Field(
        ...,
        description="The query vector. Must match the dimensionality of the index.",
        examples=[[0.1, 0.4, 0.9, 0.2]],
    )
    k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of recommendations to return.",
    )


class RecommendationResponse(BaseModel):
    """Ordered list of recommended item IDs."""

    item_ids: list[str]
    user_uid: str


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("", response_model=RecommendationResponse)
async def get_recommendations(
    body: RecommendationRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RecommendationResponse:
    """
    Return the k nearest items for the provided query vector.

    The ML index is loaded once at startup and stored in `app.state.nn_index`.
    Replace the placeholder startup data in `main.py` with real vectors loaded
    from Firestore.
    """
    index: NearestNeighborIndex | None = getattr(request.app.state, "nn_index", None)

    if index is None or not index.is_fitted:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation index is not ready yet.",
        )

    item_ids = index.query(body.vector, k=body.k)

    return RecommendationResponse(
        item_ids=item_ids,
        user_uid=current_user["uid"],
    )
