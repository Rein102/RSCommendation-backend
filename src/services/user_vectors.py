"""
User preference vector retrieval and construction.

Fetches user preferences from Firestore and builds a 14-dimensional feature
vector from the `preferences.features` sub-map, defaulting missing keys to 0.5.
"""

from fastapi import HTTPException, status
from google.cloud.firestore import Client

from src.config import WEIGHT_KEYS
from src.models.user import FeaturePreferences

DEFAULT_VALUE = 0.5


async def get_user_vector(db: Client, user_id: str) -> list[float]:
    """
    Fetch user feature preferences from Firestore and return a 14-dimensional vector.

    Reads from `users/{user_id}/preferences/features`. Any missing feature key
    defaults to 0.5 (neutral).

    Parameters
    ----------
    db:
        Firestore client instance.
    user_id:
        Firebase user UID.

    Returns
    -------
    list[float]
        14-dimensional vector in canonical WEIGHT_KEYS order.

    Raises
    ------
    HTTPException(404)
        If the user document does not exist.
    """
    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    user_data = user_doc.to_dict()
    preferences = user_data.get("preferences", {})
    features = preferences.get("features", {})

    return [features.get(key, DEFAULT_VALUE) for key in WEIGHT_KEYS]


async def get_user_preferences_raw(db: Client, user_id: str) -> dict:
    """
    Fetch the full `preferences` map for a user.

    Returns the raw dict so callers can extract both `features` and `categories`.
    Raises HTTPException(404) if the user document does not exist.
    """
    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    user_data = user_doc.to_dict()
    return user_data.get("preferences", {})


async def get_user_full_data(db: Client, user_id: str) -> dict:
    """
    Fetch the complete user document for a given UID.

    Used by the collaborative recommendations endpoint, which needs both
    `preferences.features` (to find similar historical users) and
    `activityRatings` (to exclude activities the user has already tried).

    Returns the full document as a dict. Raises HTTPException(404) if the
    user document does not exist.
    """
    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    return user_doc.to_dict() or {}
