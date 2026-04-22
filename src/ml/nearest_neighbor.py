"""
Nearest-neighbour index for recommendation inference.

Usage
-----
1. At startup, call `build_index(vectors, item_ids)` to fit the index.
2. At inference time, call `query(vector, k)` to get the k nearest item IDs,
   optionally with cosine similarity scores for re-ranking.
"""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from sklearn.neighbors import NearestNeighbors


@dataclass
class NearestNeighborIndex:
    """Wraps a scikit-learn NearestNeighbors model with item ID tracking."""

    _model: NearestNeighbors = field(default_factory=lambda: NearestNeighbors(metric="cosine"))
    _item_ids: list[str] = field(default_factory=list)
    _fitted: bool = False

    def fit(self, vectors: NDArray[np.float32], item_ids: list[str]) -> None:
        """
        Fit the index with a matrix of vectors and their corresponding item IDs.

        Parameters
        ----------
        vectors:
            Shape (n_items, n_features). One row per item.
        item_ids:
            List of item identifiers matching the row order of `vectors`.
        """
        if len(vectors) != len(item_ids):
            raise ValueError("vectors and item_ids must have the same length.")
        self._item_ids = item_ids
        self._model.fit(vectors)
        self._fitted = True

    def query(
        self,
        vector: NDArray[np.float32],
        k: int = 5,
        return_distances: bool = False,
    ) -> list[str] | list[tuple[str, float]]:
        """
        Return the k nearest item IDs for the given query vector.

        Parameters
        ----------
        vector:
            Shape (n_features,) or (1, n_features).
        k:
            Number of neighbours to return.
        return_distances:
            If True, return list of (item_id, cosine_similarity) tuples
            instead of a plain list of item IDs. Similarity = 1 - distance.

        Returns
        -------
        list[str] when return_distances=False (default).
        list[tuple[str, float]] when return_distances=True.
        """
        if not self._fitted:
            raise RuntimeError("Index has not been fitted yet. Call fit() first.")

        vec = np.array(vector, dtype=np.float32).reshape(1, -1)
        k = min(k, len(self._item_ids))
        distances, indices = self._model.kneighbors(vec, n_neighbors=k)

        if return_distances:
            return [
                (self._item_ids[i], float(1.0 - distances[0][rank]))
                for rank, i in enumerate(indices[0])
            ]

        return [self._item_ids[i] for i in indices[0]]

    @property
    def is_fitted(self) -> bool:
        return self._fitted


def build_index(vectors: NDArray[np.float32], item_ids: list[str]) -> NearestNeighborIndex:
    """
    Construct and fit a new NearestNeighborIndex.

    Call this inside the FastAPI lifespan startup handler:

        app.state.nn_index = build_index(vectors, item_ids)

    If `item_ids` is empty the index is returned in an unfitted state;
    queries against it will raise HTTP 503.
    """
    index = NearestNeighborIndex()
    if item_ids:
        index.fit(vectors, item_ids)
    return index
