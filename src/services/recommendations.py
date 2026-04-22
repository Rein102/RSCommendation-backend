"""
Recommendation service.

Orchestrates the full recommendation pipeline:
1. Read user preferences (features + categories) from Firestore in one fetch.
2. Build the 14-dim feature vector.
3. Query the NN index for a larger candidate pool (k * 3).
4. Re-rank candidates using a soft category preference boost.
5. Return the top-k activity IDs.
"""

from google.cloud.firestore import Client

from src.ml.nearest_neighbor import NearestNeighborIndex
from src.models.user import CategoryPreferences, FeaturePreferences
from src.services.user_vectors import DEFAULT_VALUE, WEIGHT_KEYS, get_user_preferences_raw

# How strongly category preference bends the NN ranking.
# Score = cosine_similarity + ALPHA * (cat_pref - 0.5)
# At ALPHA=0.3 a maximally preferred category (1.0) adds +0.15,
# a maximally disliked category (0.0) subtracts -0.15.
CATEGORY_BOOST_ALPHA = 0.3


async def get_recommendations(
    uid: str,
    k: int,
    db: Client,
    nn_index: NearestNeighborIndex,
    activity_categories: dict[str, str],
) -> list[str]:
    """
    Return the top-k recommended activity IDs for a user.

    Parameters
    ----------
    uid:
        Firebase user UID.
    k:
        Number of results to return.
    db:
        Firestore client.
    nn_index:
        Fitted nearest-neighbour index (built at startup).
    activity_categories:
        Mapping of activity doc_id → category slug, built at startup.
        Used to look up each candidate's category without a Firestore read.

    Returns
    -------
    list[str]
        Ordered list of activity document IDs, best match first.
    """
    # 1. Fetch the full preferences map once.
    preferences = await get_user_preferences_raw(db, uid)
    features_raw = preferences.get("features", {})
    categories_raw = preferences.get("categories", {})

    # 2. Build the 14-dim feature vector (missing keys → 0.5).
    feature_vector = [features_raw.get(key, DEFAULT_VALUE) for key in WEIGHT_KEYS]

    # 3. Parse category preferences; fall back to neutral defaults for missing slugs.
    category_prefs = CategoryPreferences(**{
        k: categories_raw.get(k, DEFAULT_VALUE)
        for k in CategoryPreferences.model_fields
    })

    # 4. Query the NN index for a larger candidate pool to allow re-ranking headroom.
    n_candidates = min(k * 3, len(activity_categories))
    candidates: list[tuple[str, float]] = nn_index.query(
        feature_vector, k=n_candidates, return_distances=True
    )  # type: ignore[assignment]

    # 5. Re-rank: cosine_similarity + alpha * (cat_pref - 0.5)
    scored: list[tuple[float, str]] = []
    for activity_id, similarity in candidates:
        category_slug = activity_categories.get(activity_id)
        cat_pref = category_prefs.get(category_slug) if category_slug else DEFAULT_VALUE
        final_score = similarity + CATEGORY_BOOST_ALPHA * (cat_pref - 0.5)
        scored.append((final_score, activity_id))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [activity_id for _, activity_id in scored[:k]]
