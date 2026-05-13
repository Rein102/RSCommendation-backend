# AGENTS.md

## Stack

Python 3.12, package manager: `uv` (lockfile: `uv.lock`)
FastAPI + Uvicorn, Firebase Admin SDK, Firestore, scikit-learn, numpy, pandas

## Dependency management

Always use `uv add` / `uv sync` — never `pip install`. The `.venv/` is managed by `uv` and Docker Compose mounts it as a named volume; reinstalling inside the container will break hot-reload.

## Dev commands

```bash
# Local (no Docker)
uvicorn main:app --reload --port 8000

# Full stack via Docker (preferred)
docker compose up

# After changing dependencies
docker compose up --build

# Seed Firestore (run once, idempotent)
python tools/seed_categories.py
python tools/seed_activities.py

# Build collaborative model artifacts (requires network drive access)
python tools/build_historical_profiles.py
```

## Environment setup

Requires a `.env` file at the repo root (not committed). Required keys:

```
ENVIRONMENT=development
GOOGLE_CLOUD_PROJECT=rscommendation-493408
GOOGLE_APPLICATION_CREDENTIALS=<path to ADC JSON>
```

Optional:

```
DELTA_DATA_ROOT=\\ru.nl\WrkGrp\STD-RSC-NML\Delta-datafiles
```

GCP Application Default Credentials must be present. `compose.yaml` mounts ADC and sets `GOOGLE_APPLICATION_CREDENTIALS` automatically for Docker runs.

## Architecture

### Entrypoint

`main.py:app` — FastAPI instance with a lifespan startup handler that:
1. Initialises Firebase and Firestore
2. Streams activity documents from Firestore, filters excluded IDs, builds the content-based NN index (`app.state.nn_index`)
3. Caches activity doc_id → category slug (`app.state.activity_categories`)
4. Loads historical user profile artifacts from `model_artifacts/` and builds the collaborative NN index (`app.state.historical_nn_index`)

### Shared config

`src/config.py` — single source of truth for `WEIGHT_KEYS` (the canonical 14-dim feature key order) and `EXCLUDED_ACTIVITY_IDS`. Import from here — do not redefine these constants in other modules.

### Auth

All protected routes depend on `src/dependencies.py:get_current_user`, which verifies Firebase Bearer tokens and raises HTTP 401 on failure.

### Routers

`src/routers/health.py` — public `GET /health`
`src/routers/recommendations.py` — two auth-protected endpoints:
- `GET /recommendations` — content-based
- `GET /recommendations/collaborative` — collaborative (503 if artifacts missing)

### ML

`src/ml/nearest_neighbor.py` — `NearestNeighborIndex` wraps scikit-learn `NearestNeighbors` with cosine distance and item ID tracking. Used for both the activity index and the historical user index. `build_index(vectors, item_ids)` is the entry point called from `main.py`.

### Services

`src/services/recommendations.py` — content-based pipeline: fetch user preferences, build 14-dim vector, query activity NN index, re-rank with category boost, return top-k activity IDs.

`src/services/collaborative_recommendations.py` — collaborative pipeline: query historical user NN index, collect attended activities from nearest neighbours, filter out tried and excluded activities, rank by frequency, return top-k activity IDs. Runs entirely from in-memory data; no Firestore reads.

`src/services/user_vectors.py` — Firestore helpers. `get_user_preferences_raw` returns the preferences map. `get_user_full_data` returns the complete user document including `activityRatings` (used by the collaborative endpoint to know what the user has already tried).

### Tools

`tools/seed_activities.py` — seeds the Firestore `activities` collection. Also the canonical source of activity weight vectors (used by `build_historical_profiles.py` to look up feature vectors by doc_id). Adding or changing an activity means editing this file and re-seeding.

`tools/build_historical_profiles.py` — offline training script. Reads all 39 delta_activiteit.csv files from the RSC network drive, maps Dutch `naam` values to Firestore doc IDs via the `nameNl` field in `seed_activities.py`, computes a 14-dim preference profile per historical member using the same weighted-average algorithm as the Flutter app, and writes artifacts to `model_artifacts/`. The network drive is read-only; this script never writes there.

## Recommendation flows

### Content-based (`GET /recommendations?k=10`)

1. Verify Firebase token, extract uid
2. Fetch `users/{uid}.preferences.features` and `.categories` from Firestore
3. Build 14-dim vector (missing keys default to 0.5)
4. Query activity NN index for `k * 3` candidates (cosine similarity)
5. Re-rank: `score = cosine_similarity + 0.3 * (category_pref - 0.5)`
6. Return top-k activity IDs

### Collaborative (`GET /recommendations/collaborative?k=10`)

1. Verify Firebase token, extract uid
2. Fetch full `users/{uid}` document — reads `preferences.features` and `activityRatings`
3. Build 14-dim vector from `preferences.features`
4. Extract tried activity IDs from `activityRatings` keys
5. Query historical user NN index for `k * 5` nearest historical members
6. Tally activity frequency across those members
7. Filter: remove tried activities and `EXCLUDED_ACTIVITY_IDS`
8. Return top-k by frequency

## Firestore schema

### `activities/{doc_id}`

```
name:      str            English display name
nameNl:    str            Dutch name (used for name mapping in build_historical_profiles.py)
extra:     str | None     Sub-variant label (e.g. "Basic", "Women"), null for base activities
category:  str            Category slug (e.g. "team_sports")
icon:      str | None     Flutter Material icon name
imageUrl:  str | None     Reserved for future photos; null for now
weights:   map            14 float keys (0.0-1.0):
    social, goal, energy_type, variety, intensity, strength, fitness,
    coordination, flexibility, contact, opponent, social_interaction,
    tactical, mental_calm
```

### `categories/{slug}`

```
slug:    str     Category slug (matches the document ID)
nameEn:  str     English display name
nameNl:  str     Dutch display name
icon:    str     Flutter Material icon name
```

### `users/{uid}`

Written by the Flutter client via the Firebase SDK.

```
onboardingComplete:  bool
onboardingSkipped:   bool
activityRatings:     map    activity_doc_id -> rating (1.0-5.0)
                            Keys are the activity IDs the user rated during onboarding.
                            Used by the collaborative endpoint to exclude already-tried activities.
preferences:
    features:    map    14 float keys (0.0-1.0, default 0.5) — derived from activityRatings
    categories:  map    10 float keys (0.0-1.0, default 0.5) — one per category slug
```

## Model artifacts

Generated by `tools/build_historical_profiles.py`. Stored in `model_artifacts/` (gitignored). Loaded at startup.

| File | Shape / type | Purpose |
|---|---|---|
| `historical_user_vectors.npy` | float32 (n_users, 14) | Profile vectors for the collaborative NN index |
| `historical_user_activities.json` | list[list[str]] | Per-row list of attended activity doc IDs, in the same order as the vectors |

No user identifiers are stored. The NN index uses integer row indices ("0", "1", ...) as item IDs, which map directly to positions in the activities list. If either file is missing at startup, `GET /recommendations/collaborative` returns 503. The other endpoint is unaffected.

## What agents should not do

Do not redefine `WEIGHT_KEYS` or `EXCLUDED_ACTIVITY_IDS` in any module other than `src/config.py`.

Do not write to `DELTA_DATA_ROOT` or any path under it. The network drive is read-only.

Do not modify `model_artifacts/` by hand. Re-run `tools/build_historical_profiles.py` to regenerate.

Do not change the artifact filenames without updating `main.py:_load_historical_index`.

If you add or rename an activity in `tools/seed_activities.py`, re-seed Firestore and re-run `build_historical_profiles.py`.

## Category slugs

| Slug | English name |
|---|---|
| `team_sports` | Team Sports |
| `racket_sports` | Racket Sports |
| `combat_sports` | Combat Sports |
| `dance` | Dance |
| `fitness_strength` | Fitness & Strength |
| `group_cardio` | Group Cardio |
| `mind_body` | Mind & Body |
| `individual_sports` | Individual Sports |
| `outdoor_adventure` | Outdoor & Adventure |
| `creative_cultural` | Creative & Cultural |

## Excluded activity IDs

Defined in `src/config.py:EXCLUDED_ACTIVITY_IDS`. Seeded into Firestore for metadata completeness but never returned by either recommendation endpoint.

Meet & Play formats: `meet_and_play_beach_volleyball`, `meet_and_play_basketball`, `meet_and_play_volleyball`, `meet_and_play_tennis`, `beach_volleyball_meetplay`, `volleyball_meetplay`, `tennis_meetplay`
Internal competition: `internal_comp`
Assessment & advisory services: `fms_test`, `run_analysis`, `nutrition_advice`, `nutrition_advice_medical`
Generic umbrella entries: `culture`, `mental_sport`
One-off events: `lecture`, `performance`, `workshop`, `spinning_movie`, `spinning_ftp`

## Development philosophy

Place new code in the correct module boundary immediately:

| Code type | Location |
|---|---|
| Route handlers | `src/routers/` |
| Pydantic schemas | `src/models/` |
| Business logic / services | `src/services/` |
| ML utilities | `src/ml/` |
| Firebase / infra helpers | `src/` top-level |
| Shared constants | `src/config.py` |
| One-off scripts (seeding, training) | `tools/` |

Be pragmatic: introduce abstraction only when the boundary is clear.

## Tooling

No lint, formatter, type-checker, or test runner is configured. Do not assume `pytest`, `ruff`, or `mypy` are available. No CI/CD and no pre-commit hooks. Verify changes manually.
