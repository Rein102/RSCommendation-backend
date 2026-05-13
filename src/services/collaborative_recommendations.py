"""
Collaborative recommendation service.

Uses a nearest-neighbour index over historical RSC member profiles to find
members with similar activity preferences, then recommends activities those
members attended that the current app user has not tried yet.

This runs entirely from in-memory data loaded at startup — no Firestore reads
happen inside this service. The index and activity list are built once in
main.py and passed in at call time.

No user identifiers are stored or processed here. The NN index uses integer
row indices as item IDs, which map directly to positions in the
historical_user_activities list.
"""

from collections import Counter

from src.config import EXCLUDED_ACTIVITY_IDS
from src.ml.nearest_neighbor import NearestNeighborIndex


def get_collaborative_recommendations(
    user_vector: list[float],
    tried_activity_ids: set[str],
    nn_index: NearestNeighborIndex,
    historical_user_activities: list[list[str]],
    k: int,
    n_neighbours: int | None = None,
) -> list[str]:
    """
    Return up to k activity IDs recommended via collaborative filtering.

    How it works:
      1. Find the `n_neighbours` historical members whose 14-dim profile is
         closest to the app user's profile (cosine similarity).
      2. Collect all activities those members have attended.
      3. Remove activities the user has already tried and excluded activity IDs.
      4. Rank the remaining activities by how many neighbours attended them.
      5. Return the top-k.

    Parameters
    ----------
    user_vector:
        The app user's 14-dim preference vector (same space as historical profiles).
    tried_activity_ids:
        Set of activity doc IDs the user has already tried (from onboarding
        activityRatings). These are excluded from recommendations.
    nn_index:
        Fitted NearestNeighborIndex over historical user profile vectors,
        built at startup from model_artifacts/historical_user_vectors.npy.
        Item IDs are string integers ("0", "1", ...) matching row positions
        in historical_user_activities.
    historical_user_activities:
        List of activity doc ID lists, one entry per historical member, in
        the same row order as the NN index vectors.
        Loaded at startup from model_artifacts/historical_user_activities.json.
    k:
        Number of recommendations to return.
    n_neighbours:
        How many historical neighbours to sample. Defaults to k * 5 to give
        the frequency ranking enough candidates to work with after filtering.

    Returns
    -------
    list[str]
        Activity doc IDs ordered by descending neighbour popularity.
        May be shorter than k if not enough candidates survive filtering.
    """
    if not nn_index.is_fitted:
        return []

    if n_neighbours is None:
        n_neighbours = k * 5

    # Cap at index size
    n_neighbours = min(n_neighbours, len(historical_user_activities))

    # Query returns string integers ("0", "1", ...) as item IDs
    neighbour_indices: list[str] = nn_index.query(user_vector, k=n_neighbours)

    # Tally how many neighbours attended each activity
    activity_counter: Counter[str] = Counter()
    for idx in neighbour_indices:
        for activity_id in historical_user_activities[int(idx)]:
            activity_counter[activity_id] += 1

    # Filter: exclude already tried and globally excluded activities
    blocked = tried_activity_ids | EXCLUDED_ACTIVITY_IDS
    candidates = [
        (activity_id, count)
        for activity_id, count in activity_counter.most_common()
        if activity_id not in blocked
    ]

    return [activity_id for activity_id, _ in candidates[:k]]
