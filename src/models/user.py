"""
User preference models.

User preferences are stored in Firestore under `users/{uid}` with the shape:

    {
      "onboardingComplete": bool,
      "preferences": {
        "features": {
          "social": 0.8,
          "goal": 0.4,
          ...  (14 keys, matching activity weight keys exactly)
        },
        "categories": {
          "team_sports": 0.8,
          "racket_sports": 0.3,
          ...  (10 category slug keys)
        }
      }
    }

Flutter writes this document directly via the Firebase SDK.
The backend reads it at recommendation time.
"""

from pydantic import BaseModel, Field


class FeaturePreferences(BaseModel):
    """
    User preference scores for the 14 taxonomy feature dimensions.

    Keys are identical to the `weights` keys on activity documents,
    enabling a direct 1-to-1 mapping to the NN query vector.

    All values are in [0.0, 1.0]; 0.5 represents no preference.
    """

    social:             float = Field(default=0.5, ge=0.0, le=1.0)
    goal:               float = Field(default=0.5, ge=0.0, le=1.0)
    energy_type:        float = Field(default=0.5, ge=0.0, le=1.0)
    variety:            float = Field(default=0.5, ge=0.0, le=1.0)
    intensity:          float = Field(default=0.5, ge=0.0, le=1.0)
    strength:           float = Field(default=0.5, ge=0.0, le=1.0)
    fitness:            float = Field(default=0.5, ge=0.0, le=1.0)
    coordination:       float = Field(default=0.5, ge=0.0, le=1.0)
    flexibility:        float = Field(default=0.5, ge=0.0, le=1.0)
    contact:            float = Field(default=0.5, ge=0.0, le=1.0)
    opponent:           float = Field(default=0.5, ge=0.0, le=1.0)
    social_interaction: float = Field(default=0.5, ge=0.0, le=1.0)
    tactical:           float = Field(default=0.5, ge=0.0, le=1.0)
    mental_calm:        float = Field(default=0.5, ge=0.0, le=1.0)

    def to_vector(self) -> list[float]:
        """Return values in canonical WEIGHT_KEYS order as a flat list."""
        return [
            self.social, self.goal, self.energy_type, self.variety,
            self.intensity, self.strength, self.fitness, self.coordination,
            self.flexibility, self.contact, self.opponent,
            self.social_interaction, self.tactical, self.mental_calm,
        ]


class CategoryPreferences(BaseModel):
    """
    User preference scores for each of the 10 RSC activity categories.

    Keys match the CategorySlug enum values and the Firestore
    `categories/{slug}` document IDs.

    All values are in [0.0, 1.0]; 0.5 represents no preference (neutral).
    Used as a soft re-ranking signal after the NN query — not a hard filter.
    """

    team_sports:       float = Field(default=0.5, ge=0.0, le=1.0)
    racket_sports:     float = Field(default=0.5, ge=0.0, le=1.0)
    combat_sports:     float = Field(default=0.5, ge=0.0, le=1.0)
    dance:             float = Field(default=0.5, ge=0.0, le=1.0)
    fitness_strength:  float = Field(default=0.5, ge=0.0, le=1.0)
    group_cardio:      float = Field(default=0.5, ge=0.0, le=1.0)
    mind_body:         float = Field(default=0.5, ge=0.0, le=1.0)
    individual_sports: float = Field(default=0.5, ge=0.0, le=1.0)
    outdoor_adventure: float = Field(default=0.5, ge=0.0, le=1.0)
    creative_cultural: float = Field(default=0.5, ge=0.0, le=1.0)

    def get(self, slug: str) -> float:
        """Return the preference score for a category slug, defaulting to 0.5."""
        return getattr(self, slug, 0.5)


class UserPreferences(BaseModel):
    """Combined feature and category preferences for a user."""

    features:   FeaturePreferences   = Field(default_factory=FeaturePreferences)
    categories: CategoryPreferences  = Field(default_factory=CategoryPreferences)
