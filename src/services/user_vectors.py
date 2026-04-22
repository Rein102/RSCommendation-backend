"""
User preference vector retrieval and construction.

Fetches user preferences from Firestore and builds a 14-dimensional vector
with default values (0.5) for missing categories.
"""

from google.cloud.firestore import Client
from fastapi import HTTPException, status


# The 14 taxonomy categories in order
WEIGHT_KEYS = [
    "social",
    "goal",
    "energy_type",
    "variety",
    "intensity",
    "strength",
    "fitness",
    "coordination",
    "flexibility",
    "contact",
    "opponent",
    "social_interaction",
    "tactical",
    "mental_calm",
]

DEFAULT_VALUE = 0.5


async def get_user_vector(db: Client, user_id: str) -> list[float]:
    """
    Fetch user preferences from Firestore and build a 14-dimensional vector.

    Parameters
    ----------
    db : Client
        Firestore client instance.
    user_id : str
        Firebase user UID.

    Returns
    -------
    list[float]
        14-dimensional vector with preferences, defaulting to 0.5 for missing categories.

    Raises
    ------
    HTTPException
        If the user document is not found (404).
    """
    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    user_data = user_doc.to_dict()
    preferences = user_data.get("preferences", {})

    # Build the 14-dimensional vector, filling missing categories with DEFAULT_VALUE
    vector = [preferences.get(key, DEFAULT_VALUE) for key in WEIGHT_KEYS]

    return vector
