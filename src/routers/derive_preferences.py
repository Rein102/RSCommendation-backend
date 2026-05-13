"""
Derive-preferences router.

POST /derive-preferences
    - Requires a valid Firebase ID token (Authorization: Bearer <token>)
    - Reads the authenticated user's activityRatings, current preferences,
      and manualOverrides from Firestore
    - Computes the rating-weighted preference vector
    - Preserves any keys listed in `manualOverrides` from the current stored
      preferences (per-dimension override)
    - Writes the merged result back to `users/{uid}.preferences`
    - Returns the merged preferences in the same nested
      `{ features: {...}, categories: {...} }` shape used in Firestore.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.dependencies import get_current_user
from src.models.user import CategoryPreferences, DerivePreferencesResponse, FeaturePreferences
from src.services.derive_preferences import derive_preferences

router = APIRouter(prefix="/derive-preferences", tags=["preferences"])


@router.post("", response_model=DerivePreferencesResponse)
async def derive_preferences_endpoint(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DerivePreferencesResponse:
    """Derive, merge, persist, and return the authenticated user's preferences.

    The backend reads all needed data from Firestore using the UID extracted
    from the verified Bearer token. No request body is required.
    """
    activity_weights: dict[str, dict[str, float]] = getattr(
        request.app.state, "activity_weights", None
    )
    activity_categories: dict[str, str] = getattr(
        request.app.state, "activity_categories", None
    )

    if not activity_weights or not activity_categories:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Activity cache is not ready yet.",
        )

    merged = await derive_preferences(
        uid=current_user["uid"],
        db=request.app.state.db,
        activity_weights=activity_weights,
        activity_categories=activity_categories,
    )

    return DerivePreferencesResponse(
        features=FeaturePreferences(**merged["features"]),
        categories=CategoryPreferences(**merged["categories"]),
    )
