# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

- **Language**: Python 3.12
- **Framework**: FastAPI + Uvicorn
- **ML**: scikit-learn nearest-neighbors, numpy
- **Database**: Firestore (Firebase)
- **Package Manager**: `uv` (never `pip install`)
- **Environment**: GCP Application Default Credentials required

## Running the Application

### Local Development (outside Docker)

```bash
uvicorn main:app --reload --port 8000
```

### Docker Compose (Preferred)

```bash
# Start the app
docker compose up

# Rebuild after dependency changes
docker compose up --build
```

### Seeding Data

First-time setup only (idempotent):

```bash
python tools/seed_categories.py
python tools/seed_activities.py
```

## Adding Dependencies

Use `uv` exclusively:

```bash
uv add <package-name>
uv sync
```

Do not use `pip install`. The `.venv/` is managed by `uv` and mounted as a volume in Docker; reinstalling there will break hot-reload.

## Project Architecture

### Core Layers

1. **Entrypoint** (`main.py`)
   - FastAPI app with lifespan startup handler
   - On startup: initializes Firebase, builds the k-NN index, caches activity→category mappings
   - `EXCLUDED_ACTIVITY_IDS` frozenset controls which activities are indexable
   - `WEIGHT_KEYS` canonical order must be consistent across activity weights, user preferences, and NN queries

2. **Authentication** (`src/dependencies.py`)
   - Firebase ID token verification via Bearer scheme
   - All protected routes depend on `get_current_user(token)`
   - Raises HTTP 401 on token expiry or invalidity

3. **Routers** (`src/routers/`)
   - `health.py`: Public health check endpoint
   - `recommendations.py`: Protected recommendations endpoint (`GET /recommendations?k=10`)
     - Extracts user UID from verified token
     - Validates k parameter (1–50)
     - Returns `RecommendationResponse` with ordered activity IDs

4. **Services** (`src/services/`)
   - `user_vectors.py`: Fetches user preferences from Firestore, builds feature vector
   - `recommendations.py`: Orchestrates the full recommendation pipeline

5. **Models** (`src/models/`)
   - `category.py`: CategorySlug enum (10 categories) and Category schema
   - `user.py`: FeaturePreferences (14 dims), CategoryPreferences (10 dims), UserPreferences (combined)
   - `recommendations.py`: RecommendationResponse schema

6. **ML** (`src/ml/`)
   - `nearest_neighbor.py`: NearestNeighborIndex wraps scikit-learn's KNeighbors with item ID tracking
   - Fits on startup from activity vectors; queried at recommendation time

### Recommendation Pipeline

1. Client sends `GET /recommendations?k=10` with Firebase token
2. Backend verifies token → extract uid
3. Fetch full `users/{uid}` preferences document from Firestore (one call)
4. Build 14-dim feature vector from `preferences.features` (missing keys → 0.5)
5. Query k-NN index for k×3 candidates using cosine distance
6. Re-rank with category boost: `score = similarity + 0.3 * (category_pref - 0.5)`
7. Return top-k activity IDs

The "k×3 candidates" strategy allows category preferences to reorder results without hard-filtering out non-preferred categories.

## Data Model

### Activity Document (`activities/{doc_id}`)

```
name:      str            English display name
nameNl:    str            Dutch name
extra:     str | None     Sub-variant label (e.g. "Basic", "Women")
category:  str            Category slug (e.g. "team_sports")
icon:      str | None     Flutter Material icon name
imageUrl:  str | None     Reserved; null for now
weights:   map[str, float]
  - 14 keys: social, goal, energy_type, variety, intensity, strength, fitness,
    coordination, flexibility, contact, opponent, social_interaction, tactical, mental_calm
  - Values: 0.0–1.0
```

### Category Document (`categories/{slug}`)

```
slug:   str    Category slug (matches document ID)
nameEn: str    English display name
nameNl: str    Dutch display name
icon:   str    Flutter Material icon name
```

### User Document (`users/{uid}`)

Written by Flutter client via Firebase SDK.

```
onboardingComplete: bool
preferences:
  features:   map[str, float]  — 14 dims matching activity weights (0.0–1.0, default 0.5)
  categories: map[str, float]  — 10 dims, one per category slug (0.0–1.0, default 0.5)
```

## Code Organization

Place new code following this structure:

| Code Type | Location |
|---|---|
| Route handlers | `src/routers/` |
| Pydantic schemas | `src/models/` |
| Business logic | `src/services/` |
| ML utilities | `src/ml/` |
| Firebase/infra helpers | `src/` (top-level) |

Keep abstraction pragmatic: introduce it only when the boundary becomes clear.

## Key Implementation Details

### Startup Sequence

1. `get_app()` initializes Firebase Admin SDK using Application Default Credentials
2. `get_db()` returns Firestore client
3. Stream all documents from `activities` collection
4. Filter: keep only docs with a `weights` map and not in `EXCLUDED_ACTIVITY_IDS`
5. Build in-memory `activity_categories` dict (`doc_id` → `category slug`) for fast lookup during re-ranking
6. Extract 14-dim vectors from activity weights, build and fit the k-NN index

### Category Re-Ranking

The `CATEGORY_BOOST_ALPHA = 0.3` constant controls how strongly category preferences affect ranking. At ALPHA=0.3:
- Maximally preferred category (1.0): +0.15 boost
- Maximally disliked category (0.0): -0.15 penalty
- Neutral (0.5): no change

### Vector Semantics

All 14-dim vectors use the same key order:

```python
["social", "goal", "energy_type", "variety", "intensity", "strength", "fitness",
 "coordination", "flexibility", "contact", "opponent", "social_interaction", "tactical", "mental_calm"]
```

This order appears in:
- Activity `weights` documents
- User `preferences.features` maps
- The NN query vector construction

Mismatches will silently produce incorrect recommendations.

## Environment Setup

- `.env` file at repo root (not committed; ask team for values)
  - `ENVIRONMENT=development` — allows relaxed CORS
  - `GOOGLE_CLOUD_PROJECT=rscommendation-493408` — Firebase project ID
  - `GOOGLE_APPLICATION_CREDENTIALS` — path to ADC JSON file (OS-specific)
- GCP Application Default Credentials required:
  ```bash
  gcloud auth application-default login
  ```
  Creates credentials at `~/.config/gcloud/application_default_credentials.json` (macOS/Linux) or `%APPDATA%\gcloud\application_default_credentials.json` (Windows)
- Docker Compose automatically mounts ADC and sets env vars

## Known Limitations

- No linting, formatting, or type-checking configured (no `pytest`, `ruff`, or `mypy`)
- No CI/CD pipelines (no `.github/workflows/`)
- No pre-commit hooks
- CORS is wide-open (`allow_origins=["*"]`) — restrict before production
- Manual verification required for all changes

## Excluded Activities

The following are in Firestore for metadata completeness but never indexed:

- Meet & Play formats (7 IDs)
- Internal competition
- Assessment/advisory services (4 IDs)
- Generic umbrella entries (2 IDs)
- One-off events (5 IDs)

See `EXCLUDED_ACTIVITY_IDS` in `main.py` for the full set. Edit there and reseed to change.

## Firebase Project

- **Project ID**: `rscommendation-493408`
- **Firestore Database**: default (auto-created)
- **Authentication**: Firebase Auth (ID tokens verified by backend)
- **Collections**:
  - `activities` — activity catalogue with weights
  - `categories` — category metadata
  - `users` — user preference documents (written by Flutter client)
