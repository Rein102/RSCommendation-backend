"""
Derive a user's preference vector from their raw activity ratings.

Algorithm (port of the previous Flutter `ActivityPreferenceService`):

For each of the 14 feature keys:
    feature[k] = Σ(norm_rating × activity_weight[k]) / Σ(norm_rating)
where `norm_rating = rating / 5.0`. Defaults to 0.5 when no rated activity
contributes to that key.

For each of the 10 category slugs:
    category[slug] = mean(norm_rating) across all rated activities in that slug.
Defaults to 0.5 when the user has rated nothing in that category.

Per-dimension manual override merge:
    For each key in `users/{uid}.manualOverrides`, the existing value in
    `users/{uid}.preferences` is preserved instead of the freshly-derived one.

The merged result is written back to `users/{uid}.preferences` (Firestore merge)
and also returned to the caller.
"""

from typing import Any

from fastapi import HTTPException, status
from google.cloud.firestore import Client

from src.models.category import CategorySlug
from src.services.user_vectors import DEFAULT_VALUE, WEIGHT_KEYS

# Derived from the canonical CategorySlug enum so this list stays in sync
# automatically if new categories are ever added.
CATEGORY_SLUGS: list[str] = [slug.value for slug in CategorySlug]


def _derive_pure(
    activity_ratings: dict[str, float],
    activity_weights: dict[str, dict[str, float]],
    activity_categories: dict[str, str],
) -> tuple[dict[str, float], dict[str, float]]:
    """Pure rating-weighted derivation, ignoring manual overrides.

    Returns
    -------
    (features, categories)
        Two dicts keyed on the canonical feature/category slugs, each value
        clamped to [0.0, 1.0]. Missing data → 0.5.
    """
    feature_sums:   dict[str, float] = {}
    feature_totals: dict[str, float] = {}
    category_sums:   dict[str, float] = {}
    category_counts: dict[str, int] = {}

    for activity_id, raw_rating in activity_ratings.items():
        weights = activity_weights.get(activity_id)
        if weights is None:
            # Unknown activity id (e.g. excluded from the NN cache) — skip.
            continue

        norm_rating = float(raw_rating) / 5.0
        if norm_rating == 0.0:
            # A zero-rating contributes nothing to any dimension — skip rather
            # than letting it dilute category counts without affecting features.
            continue

        for key in WEIGHT_KEYS:
            weight = weights.get(key, DEFAULT_VALUE)
            feature_sums[key]   = feature_sums.get(key,   0.0) + norm_rating * weight
            feature_totals[key] = feature_totals.get(key, 0.0) + norm_rating

        slug = activity_categories.get(activity_id)
        if slug is not None:
            category_sums[slug]   = category_sums.get(slug,   0.0) + norm_rating
            category_counts[slug] = category_counts.get(slug, 0)   + 1

    def feature(key: str) -> float:
        total = feature_totals.get(key, 0.0)
        if total == 0.0:
            return DEFAULT_VALUE
        return max(0.0, min(1.0, feature_sums[key] / total))

    def category(slug: str) -> float:
        count = category_counts.get(slug, 0)
        if count == 0:
            return DEFAULT_VALUE
        return max(0.0, min(1.0, category_sums[slug] / count))

    return (
        {k: feature(k)  for k in WEIGHT_KEYS},
        {s: category(s) for s in CATEGORY_SLUGS},
    )


async def derive_preferences(
    uid: str,
    db: Client,
    activity_weights: dict[str, dict[str, float]],
    activity_categories: dict[str, str],
) -> dict[str, dict[str, float]]:
    """Derive, merge, persist, and return the user's preferences.

    Reads `users/{uid}.activityRatings`, `users/{uid}.preferences`, and
    `users/{uid}.manualOverrides`. Computes the pure rating-derived vector,
    then overwrites any key listed in `manualOverrides` with the existing
    stored value. Persists the merged result back to
    `users/{uid}.preferences` (Firestore set with merge=True).

    Parameters
    ----------
    uid:
        Firebase user UID extracted from the verified Bearer token.
    db:
        Firestore client (Firebase Admin SDK).
    activity_weights:
        In-memory map of activity doc_id → 14-key feature weights, built at
        startup.
    activity_categories:
        In-memory map of activity doc_id → category slug, built at startup.

    Returns
    -------
    dict
        `{ "features": {...}, "categories": {...} }` — the merged preferences
        that were just written to Firestore.

    Raises
    ------
    HTTPException(404)
        If the `users/{uid}` document does not exist.
    """
    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {uid} not found.",
        )

    user_data: dict[str, Any] = user_doc.to_dict() or {}

    raw_ratings:   dict[str, Any] = user_data.get("activityRatings", {}) or {}
    current_prefs: dict[str, Any] = user_data.get("preferences", {}) or {}
    overrides_raw: Any            = user_data.get("manualOverrides", []) or []

    # Coerce ratings to floats. Skip any non-numeric junk silently.
    activity_ratings: dict[str, float] = {}
    for activity_id, value in raw_ratings.items():
        try:
            activity_ratings[str(activity_id)] = float(value)
        except (TypeError, ValueError):
            continue

    derived_features, derived_categories = _derive_pure(
        activity_ratings=activity_ratings,
        activity_weights=activity_weights,
        activity_categories=activity_categories,
    )

    manual_overrides: set[str] = {str(k) for k in overrides_raw if isinstance(k, str)}

    current_features:   dict[str, Any] = current_prefs.get("features",   {}) or {}
    current_categories: dict[str, Any] = current_prefs.get("categories", {}) or {}

    # Merge: keep override values from current preferences, otherwise derived.
    merged_features: dict[str, float] = {}
    for key in WEIGHT_KEYS:
        if key in manual_overrides and key in current_features:
            try:
                merged_features[key] = max(0.0, min(1.0, float(current_features[key])))
            except (TypeError, ValueError):
                merged_features[key] = derived_features[key]
        else:
            merged_features[key] = derived_features[key]

    merged_categories: dict[str, float] = {}
    for slug in CATEGORY_SLUGS:
        if slug in manual_overrides and slug in current_categories:
            try:
                merged_categories[slug] = max(0.0, min(1.0, float(current_categories[slug])))
            except (TypeError, ValueError):
                merged_categories[slug] = derived_categories[slug]
        else:
            merged_categories[slug] = derived_categories[slug]

    merged: dict[str, dict[str, float]] = {
        "features":   merged_features,
        "categories": merged_categories,
    }

    user_ref.set({"preferences": merged}, merge=True)

    return merged
