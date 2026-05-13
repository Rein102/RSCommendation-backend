"""
Build historical user profiles from RSC delta activity CSV files.

Reads all delta_activiteit.csv files from the network drive, maps Dutch
activity names to Firestore activity doc IDs, and computes a 14-dim preference
profile for each historical member using the exact same weighted-average
algorithm as the Flutter app's ActivityPreferenceService.

Usage (from the backend repo root):

    python tools/build_historical_profiles.py

    # Override the data root at runtime:
    python tools/build_historical_profiles.py --data-root "//ru.nl/WrkGrp/..."

    # Or set DELTA_DATA_ROOT in your .env file.

Output (written to model_artifacts/ next to this repo):

    historical_user_vectors.npy      — float32 array (n_users, 14)
    historical_user_ids.json         — list of klant_hash strings, same row order
    historical_user_activities.json  — {klant_hash: [activity_doc_ids attended]}

After running, restart the backend — it loads these files at startup.
"""

import sys
import os
import json
import logging
import argparse

import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Make the repo root importable so we can pull from tools/seed_activities.py
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

load_dotenv(os.path.join(_REPO_ROOT, ".env"))

from tools.seed_activities import ACTIVITIES  # noqa: E402
from src.config import WEIGHT_KEYS, EXCLUDED_ACTIVITY_IDS  # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DATA_ROOT = r"\\ru.nl\WrkGrp\STD-RSC-NML\Delta-datafiles"
ARTIFACTS_DIR = os.path.join(_REPO_ROOT, "model_artifacts")

DELTA_FOLDERS: list[str] = [
    "delta1_2023_02",  "delta2_2023_03",  "delta3_2023_04",
    "delta4_2023_05",  "delta5_2023_06",  "delta6_2023_07",
    "delta7_2023_08",  "delta8_2023_09",  "delta9_2023_10",
    "delta10_2023_11", "delta11_2023_12", "delta12_2024_01",
    "delta13_2024_02", "delta14_2024_03", "delta15_2024_04",
    "delta16_2024_05", "delta17_2024_06", "delta18_2024_07",
    "delta19_2024_08", "delta20_2024_09", "delta21_2024_10",
    "delta22_2024_11", "delta23_2024_12", "delta25_2025_01",
    "delta26_2025_02", "delta27_2025_03", "delta28_2025_04",
    "delta29_2025_05", "delta30_2025_06", "delta31_2025_07",
    "delta32_2025_08", "delta33_2025_09", "delta34_2025_10",
    "delta35_2025_11", "delta36_2025_12", "delta37_2026_01",
    "delta38_2026_02", "delta39_2026_03",
]

ACTIVITY_FILE = "delta_activiteit.csv"
USER_COL = "klant_hash"
ACTIVITY_COL = "naam"
ATTENDED_COL = "geprint"
ATTENDED_VAL = "aanwezig"

# Users with fewer unique activities than this are excluded from the output.
# Too-sparse histories produce noisy profile vectors.
MIN_UNIQUE_ACTIVITIES = 3


# ---------------------------------------------------------------------------
# Step 1 — Build name → doc_id mapping and weight lookup
# ---------------------------------------------------------------------------

def build_name_mapping() -> dict[str, str]:
    """
    Map lowercase Dutch activity names (nameNl) to Firestore activity doc IDs.

    When multiple activities share the same nameNl (e.g. "Body workout" covers
    Basic, Shape, and Cardio variants), the base activity (extra=None) is
    preferred. If all candidates have an extra label, the first is used.

    Activities in EXCLUDED_ACTIVITY_IDS are included in the mapping so they
    can be counted in attendance history, but they are filtered out later
    at the profile-building and recommendation stages.
    """
    candidates: dict[str, list[tuple[str, str | None]]] = {}
    for doc_id, _en, name_nl, extra, *_ in ACTIVITIES:
        key = name_nl.strip().lower()
        candidates.setdefault(key, []).append((doc_id, extra))

    mapping: dict[str, str] = {}
    for key, options in candidates.items():
        base = [doc_id for doc_id, extra in options if extra is None]
        mapping[key] = base[0] if base else options[0][0]

    log.info(f"Name mapping built: {len(mapping)} Dutch names")
    return mapping


def build_activity_weight_lookup() -> dict[str, list[float]]:
    """
    Return {doc_id: [14 normalised floats]} for every activity.
    Raw 1-5 scores from seed_activities.py are divided by 5, matching Firestore.
    """
    return {
        doc_id: [round(s / 5, 2) for s in scores]
        for doc_id, _en, _nl, _extra, _cat, _icon, scores in ACTIVITIES
    }


# ---------------------------------------------------------------------------
# Step 2 — Load all delta CSVs
# ---------------------------------------------------------------------------

def load_all_deltas(data_root: str) -> pd.DataFrame:
    """Read only the three relevant columns from every delta folder."""
    frames: list[pd.DataFrame] = []
    missing: list[str] = []

    for folder in DELTA_FOLDERS:
        path = os.path.join(data_root, folder, ACTIVITY_FILE)
        if not os.path.exists(path):
            missing.append(folder)
            continue
        try:
            df = pd.read_csv(
                path,
                sep=",",
                usecols=[USER_COL, ACTIVITY_COL, ATTENDED_COL],
                dtype=str,
                low_memory=False,
            )
            frames.append(df)
            log.info(f"Loaded  {folder}  ({len(df):,} rows)")
        except Exception as exc:
            log.warning(f"Could not read {folder}: {exc}")

    if missing:
        log.warning(f"Folders not found on disk (skipped): {missing}")

    if not frames:
        raise RuntimeError(
            "No data loaded. Verify that the network drive is mounted "
            "and --data-root points to the correct location."
        )

    combined = pd.concat(frames, ignore_index=True)
    log.info(f"Total rows: {len(combined):,}")
    return combined


# ---------------------------------------------------------------------------
# Step 3 — Aggregate per-user activity counts
# ---------------------------------------------------------------------------

def aggregate_user_counts(
    df: pd.DataFrame,
    name_mapping: dict[str, str],
) -> dict[str, dict[str, int]]:
    """
    Return {klant_hash: {activity_doc_id: attendance_count}} for attended rows.
    Rows whose naam doesn't map to a known activity are skipped.
    """
    attended = df[df[ATTENDED_COL].str.strip() == ATTENDED_VAL].copy()
    log.info(f"Attended rows: {len(attended):,}")

    # Vectorised name lookup
    attended["doc_id"] = (
        attended[ACTIVITY_COL].str.strip().str.lower().map(name_mapping)
    )

    unmapped = attended.loc[attended["doc_id"].isna(), ACTIVITY_COL].unique()
    if len(unmapped):
        log.warning(
            f"{len(unmapped)} unrecognised activity names will be skipped. "
            f"First examples: {sorted(unmapped)[:10]}"
        )

    attended = attended.dropna(subset=["doc_id"])

    # Count per (user, activity) pair
    counts_df = (
        attended.groupby([USER_COL, "doc_id"])
        .size()
        .reset_index(name="count")
    )

    # Convert to nested dict
    user_counts: dict[str, dict[str, int]] = {
        klant_hash: dict(zip(group["doc_id"], group["count"].astype(int)))
        for klant_hash, group in counts_df.groupby(USER_COL)
    }

    log.info(f"Users with at least one mapped activity: {len(user_counts):,}")
    return user_counts


# ---------------------------------------------------------------------------
# Step 4 — Derive 14-dim profile vectors
# ---------------------------------------------------------------------------

def derive_profile(
    activity_counts: dict[str, int],
    weight_lookup: dict[str, list[float]],
) -> np.ndarray:
    """
    Compute a 14-dim preference profile for one historical user.

    Algorithm mirrors ActivityPreferenceService.deriveFromActivityRatings
    in the Flutter app exactly:

        profile[k] = Σ(normalised_count_i × weight_i_k) / Σ(normalised_count_i)

    Attendance counts are normalised by the user's personal maximum so that the
    most-attended activity gets weight 1.0 and others scale proportionally —
    the same effect as a 1-5 star rating in the app.

    Any dimension with no contributing data defaults to 0.5 (neutral).
    Activities in EXCLUDED_ACTIVITY_IDS contribute to the profile but are later
    filtered out at recommendation time.
    """
    if not activity_counts:
        return np.full(len(WEIGHT_KEYS), 0.5, dtype=np.float32)

    max_count = max(activity_counts.values())
    sums = np.zeros(len(WEIGHT_KEYS), dtype=np.float64)
    total_w = np.zeros(len(WEIGHT_KEYS), dtype=np.float64)

    for doc_id, count in activity_counts.items():
        weights = weight_lookup.get(doc_id)
        if weights is None:
            continue
        norm = count / max_count
        w = np.array(weights, dtype=np.float64)
        sums += norm * w
        total_w += norm

    profile = np.where(total_w > 0, sums / total_w, 0.5)
    return np.clip(profile, 0.0, 1.0).astype(np.float32)


# ---------------------------------------------------------------------------
# Step 5 — Save artifacts
# ---------------------------------------------------------------------------

def save_artifacts(
    vectors: np.ndarray,
    user_activities: list[list[str]],
) -> None:
    """
    Save the two artifacts the backend needs at startup.

    No user identifiers are stored. The row index in `vectors` is the only
    link to the corresponding entry in `user_activities`.
    """
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    vectors_path    = os.path.join(ARTIFACTS_DIR, "historical_user_vectors.npy")
    activities_path = os.path.join(ARTIFACTS_DIR, "historical_user_activities.json")

    np.save(vectors_path, vectors)
    log.info(f"Saved vectors    → {vectors_path}  shape={vectors.shape}")

    with open(activities_path, "w", encoding="utf-8") as f:
        json.dump(user_activities, f)
    log.info(f"Saved activities → {activities_path}  ({len(user_activities):,} users)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(data_root: str) -> None:
    log.info("=== Building historical user profiles ===")
    log.info(f"Data root : {data_root}")
    log.info(f"Artifacts : {ARTIFACTS_DIR}")

    name_mapping  = build_name_mapping()
    weight_lookup = build_activity_weight_lookup()

    raw = load_all_deltas(data_root)
    user_counts = aggregate_user_counts(raw, name_mapping)

    log.info("Deriving 14-dim profiles ...")
    vectors: list[np.ndarray] = []
    user_activities: list[list[str]] = []
    skipped = 0

    for counts in user_counts.values():
        # Filter excluded activities from the attended list stored for filtering,
        # but keep them in counts when computing the profile so the vector
        # reflects the user's full activity mix.
        non_excluded = {k: v for k, v in counts.items() if k not in EXCLUDED_ACTIVITY_IDS}

        if len(non_excluded) < MIN_UNIQUE_ACTIVITIES:
            skipped += 1
            continue

        profile = derive_profile(counts, weight_lookup)
        vectors.append(profile)
        # Only store non-excluded activities — these are what can be recommended.
        # No user identifier is stored; row index is the only link.
        user_activities.append(list(non_excluded.keys()))

    log.info(
        f"Profiles ready: {len(vectors):,}  "
        f"(skipped {skipped:,} users with < {MIN_UNIQUE_ACTIVITIES} "
        f"non-excluded unique activities)"
    )

    vectors_array = np.stack(vectors, axis=0)
    save_artifacts(vectors_array, user_activities)

    log.info("Done. Restart the backend to load the new artifacts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build historical RSC member profiles for collaborative recommendations."
    )
    parser.add_argument(
        "--data-root",
        default=os.getenv("DELTA_DATA_ROOT", DEFAULT_DATA_ROOT),
        help=(
            "Root folder containing the delta_YYYY_MM subfolders. "
            "Defaults to DELTA_DATA_ROOT env var or the RSC network path."
        ),
    )
    args = parser.parse_args()
    main(args.data_root)
