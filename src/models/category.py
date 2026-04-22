"""
Category model and slug definitions.

The 10 RSC activity categories are identified by readable string slugs
throughout the codebase, Firestore, and user preference documents.
"""

from enum import Enum

from pydantic import BaseModel


class CategorySlug(str, Enum):
    team_sports       = "team_sports"
    racket_sports     = "racket_sports"
    combat_sports     = "combat_sports"
    dance             = "dance"
    fitness_strength  = "fitness_strength"
    group_cardio      = "group_cardio"
    mind_body         = "mind_body"
    individual_sports = "individual_sports"
    outdoor_adventure = "outdoor_adventure"
    creative_cultural = "creative_cultural"


# Maps the legacy int (1–10) used in old Firestore documents to the canonical slug.
# Used by the seed script and any migration helpers.
CATEGORY_INT_TO_SLUG: dict[int, CategorySlug] = {
    1:  CategorySlug.team_sports,
    2:  CategorySlug.racket_sports,
    3:  CategorySlug.combat_sports,
    4:  CategorySlug.dance,
    5:  CategorySlug.fitness_strength,
    6:  CategorySlug.group_cardio,
    7:  CategorySlug.mind_body,
    8:  CategorySlug.individual_sports,
    9:  CategorySlug.outdoor_adventure,
    10: CategorySlug.creative_cultural,
}


class Category(BaseModel):
    """Firestore `categories/{slug}` document schema."""

    slug:   CategorySlug
    nameEn: str
    nameNl: str
    icon:   str | None = None
