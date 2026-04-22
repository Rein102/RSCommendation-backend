"""
Seed the Firestore `categories` collection with the 10 RSC activity categories.

Usage (from the backend repo root):
    python tools/seed_categories.py

Requires GCP Application Default Credentials:
    gcloud auth application-default login

Uses `set()` (not `create()`), so it is idempotent — safe to re-run.
Document IDs match the CategorySlug enum values (e.g. "team_sports").

Document schema
---------------
    slug    str            Category slug — matches the document ID
    nameEn  str            English display name
    nameNl  str            Dutch display name
    icon    str | None     Flutter Material icon name
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from src.firebase import get_app, get_db
from src.models.category import CategorySlug

load_dotenv()

# (slug, nameEn, nameNl, icon)
CATEGORIES: list[tuple[CategorySlug, str, str, str | None]] = [
    (CategorySlug.team_sports,       "Team Sports",        "Teamsporten",          "groups"),
    (CategorySlug.racket_sports,     "Racket Sports",      "Racketsport",          "sports_tennis"),
    (CategorySlug.combat_sports,     "Combat Sports",      "Vechtsporten",         "sports_martial_arts"),
    (CategorySlug.dance,             "Dance",              "Dans",                 "music_note"),
    (CategorySlug.fitness_strength,  "Fitness & Strength", "Fitness & Kracht",     "fitness_center"),
    (CategorySlug.group_cardio,      "Group Cardio",       "Groepscardio",         "directions_bike"),
    (CategorySlug.mind_body,         "Mind & Body",        "Mind & Body",          "self_improvement"),
    (CategorySlug.individual_sports, "Individual Sports",  "Individuele sporten",  "directions_run"),
    (CategorySlug.outdoor_adventure, "Outdoor & Adventure","Buiten & Avontuur",    "landscape"),
    (CategorySlug.creative_cultural, "Creative & Cultural","Creatief & Cultureel", "palette"),
]


def seed() -> None:
    print("Initialising Firebase…")
    get_app()
    db = get_db()

    collection = db.collection("categories")
    batch = db.batch()

    for slug, name_en, name_nl, icon in CATEGORIES:
        data = {
            "slug":   slug.value,
            "nameEn": name_en,
            "nameNl": name_nl,
            "icon":   icon,
        }
        ref = collection.document(slug.value)
        batch.set(ref, data)
        print(f"  Queued: {slug.value}")

    batch.commit()
    print(f"Done — seeded {len(CATEGORIES)} categories into `categories` collection.")


if __name__ == "__main__":
    seed()
