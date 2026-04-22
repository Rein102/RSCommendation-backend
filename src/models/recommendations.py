"""
Recommendation request/response schemas.
"""

from pydantic import BaseModel


class RecommendationResponse(BaseModel):
    """Ordered list of recommended activity IDs."""

    item_ids: list[str]
    user_uid: str
