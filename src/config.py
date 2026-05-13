"""
Shared configuration constants.

Centralising WEIGHT_KEYS and EXCLUDED_ACTIVITY_IDS here avoids the previous
duplication between main.py and src/services/user_vectors.py, and lets new
modules (e.g. collaborative recommendations) import them without creating
circular dependencies.
"""

# Canonical order of the 14 taxonomy feature keys.
# This order must be consistent across:
#   - activity weights documents in Firestore
#   - user preferences.features documents in Firestore
#   - NN query vector construction
#   - historical user profile vectors built by tools/build_historical_profiles.py
WEIGHT_KEYS: list[str] = [
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

# Activity doc IDs that are never included in any recommendation result.
# These are seeded into Firestore for metadata completeness (so the Flutter
# app can look up their details) but are excluded from both the content-based
# NN index and the collaborative recommendation pipeline.
EXCLUDED_ACTIVITY_IDS: frozenset[str] = frozenset({
    # Meet & Play event formats
    "meet_and_play_beach_volleyball",
    "meet_and_play_basketball",
    "meet_and_play_volleyball",
    "meet_and_play_tennis",
    "beach_volleyball_meetplay",
    "volleyball_meetplay",
    "tennis_meetplay",
    # Internal competition event
    "internal_comp",
    # Assessment & advisory services
    "fms_test",
    "run_analysis",
    "nutrition_advice",
    "nutrition_advice_medical",
    # Generic cultural/coaching umbrella entries
    "culture",
    "mental_sport",
    # One-off events
    "lecture",
    "performance",
    "workshop",
    "spinning_movie",
    "spinning_ftp",
})
