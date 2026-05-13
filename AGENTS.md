# AGENTS.md

## Stack

- Python 3.12, package manager: **`uv`** (lockfile: `uv.lock`)
- FastAPI + Uvicorn, Firebase Admin SDK, Firestore, scikit-learn, numpy

## Dependency management

- Always use `uv add` / `uv sync` — **never `pip install`**
- `.venv/` is managed by `uv`; Docker Compose mounts it as a named volume (don't reinstall inside the container)

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
```

## Environment setup

- Requires a `.env` file at the repo root (not committed — check with the team for required keys)
- Requires GCP Application Default Credentials at `~/.config/gcloud/application_default_credentials.json`
- Firebase project: `rscommendation-493408`
- `compose.yaml` mounts ADC and sets `GOOGLE_APPLICATION_CREDENTIALS` automatically for Docker runs

## Architecture

- **Entrypoint**: `main.py:app` — FastAPI instance; lifespan startup initialises Firebase, builds the NN index, and caches the activity→category map plus the activity-weights lookup
- **Auth**: all protected routes use `src/dependencies.py:get_current_user` — verifies Firebase Bearer tokens, raises HTTP 401 on failure
- **Routers**:
    - `src/routers/health.py` (public `GET /health`)
    - `src/routers/recommendations.py` (auth-protected `GET /recommendations`)
    - `src/routers/derive_preferences.py` (auth-protected `POST /derive-preferences`)
- **ML index**: built at startup from Firestore `activities` collection (excluding `EXCLUDED_ACTIVITY_IDS`), stored at `app.state.nn_index`
- **Activity category cache**: `app.state.activity_categories: dict[str, str]` — maps activity doc_id → category slug, built at startup to avoid per-request Firestore reads during re-ranking
- **Activity weights cache**: `app.state.activity_weights: dict[str, dict[str, float]]` — maps activity doc_id → 14-key feature weights map. Consumed by the derive-preferences service to compute the rating-weighted feature average without re-fetching the activities collection.
- **Models**: Pydantic schemas in `src/models/` — `category.py`, `user.py`, `recommendations.py`
- **Services**: business logic in `src/services/` — `user_vectors.py`, `recommendations.py`, `derive_preferences.py`

## Recommendation flow

1. Client sends `GET /recommendations?k=10` with a Firebase ID token
2. Backend extracts `uid` from the verified token
3. `src/services/recommendations.py:get_recommendations()`:
   a. Fetches `users/{uid}` from Firestore — reads `preferences.features` and `preferences.categories` in one call
   b. Builds 14-dim feature vector (missing keys default to 0.5)
   c. Queries the NN index for `k * 3` candidates with cosine similarity scores
   d. Re-ranks: `score = cosine_similarity + 0.3 * (category_pref - 0.5)`
   e. Returns top-k activity IDs
4. Response: `{ item_ids: [...], user_uid: "..." }`

## Derive-preferences flow

1. Client sends `POST /derive-preferences` (no body) with a Firebase ID token
2. Backend extracts `uid` from the verified token
3. `src/services/derive_preferences.py:derive_preferences()`:
   a. Reads `users/{uid}` — gets `activityRatings`, current `preferences`, and `manualOverrides`
   b. Computes pure rating-weighted derivation:
      - For each of 14 feature keys: `Σ(norm_rating × activity_weight) / Σ(norm_rating)` (default 0.5)
      - For each of 10 category slugs: `mean(norm_rating)` across rated activities in that slug (default 0.5)
      - `norm_rating = rating / 5.0`
   c. Merges with manual overrides: for each key in `manualOverrides`, keeps the current value from `users/{uid}.preferences` instead of the derived one
   d. Writes merged result to `users/{uid}.preferences` (Firestore merge)
4. Response: `{ features: {...}, categories: {...} }` — the merged preferences

Used by Flutter after any change that affects ratings (onboarding finish,
adding/removing/re-rating an activity in Profile → Activities, or the "Reset
based on tried sports" button on Profile → Preferences).

## Firestore schema

### `activities/{doc_id}`

```
name:      str            English display name
nameNl:    str            Dutch name
extra:     str | None     Sub-variant label (e.g. "Basic", "Women"), null for base activities
category:  str            Category slug (e.g. "team_sports") — see CategorySlug enum
icon:      str | None     Flutter Material icon name
imageUrl:  str | None     Reserved for future photos; null for now
weights:   map            14 float keys (0.0–1.0):
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

Mostly written directly by the Flutter client via the Firebase SDK. The
`preferences` field is written by the backend's `POST /derive-preferences`
endpoint.

```
onboardingComplete:  bool
activityRatings:     map    activity_id → float rating (1.0–5.0)
                            Raw ratings the user has given activities.
                            Owned by Flutter.
preferences:                Derived + override-merged preference vector.
                            Owned by the backend (POST /derive-preferences).
    features:    map    14 float keys matching activity weight keys (0.0–1.0, default 0.5)
        social, goal, energy_type, variety, intensity, strength, fitness,
        coordination, flexibility, contact, opponent, social_interaction,
        tactical, mental_calm
    categories:  map    10 float keys matching category slugs (0.0–1.0, default 0.5)
        team_sports, racket_sports, combat_sports, dance, fitness_strength,
        group_cardio, mind_body, individual_sports, outdoor_adventure, creative_cultural
manualOverrides:     list[str]  Preference keys (mix of 14 feature keys + 10
                                category slugs) the user has manually adjusted.
                                The derive-preferences endpoint preserves the
                                existing value of these keys instead of
                                overwriting with the freshly-derived one.
                                Owned by Flutter. Missing → treated as empty.
```

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

The following activity doc IDs are seeded into the Firestore `activities` collection
(so the Flutter app can look up their metadata) but are **excluded from the NN index**
at startup via `EXCLUDED_ACTIVITY_IDS` in `main.py`. They will never appear in
recommendation results.

- Meet & Play formats: `meet_and_play_beach_volleyball`, `meet_and_play_basketball`, `meet_and_play_volleyball`, `meet_and_play_tennis`, `beach_volleyball_meetplay`, `volleyball_meetplay`, `tennis_meetplay`
- Internal competition: `internal_comp`
- Assessment & advisory services: `fms_test`, `run_analysis`, `nutrition_advice`, `nutrition_advice_medical`
- Generic umbrella entries: `culture`, `mental_sport`
- One-off events: `lecture`, `performance`, `workshop`, `spinning_movie`, `spinning_ftp`

## Development philosophy

Structure for rapid scaling from the start. Place new code in the correct module boundary immediately:

| Code type | Location |
|---|---|
| Route handlers | `src/routers/` |
| Pydantic schemas | `src/models/` |
| Business logic / services | `src/services/` |
| ML utilities | `src/ml/` |
| Firebase / infra helpers | `src/` top-level |

Be pragmatic: introduce the right abstraction when it's clearly needed, not speculatively.

## Tooling — nothing configured yet

No lint, formatter, type-checker, or test runner is set up. Do not assume `pytest`, `ruff`, or `mypy` are available. No CI/CD (no `.github/workflows/`) and no pre-commit hooks — verify changes manually.
