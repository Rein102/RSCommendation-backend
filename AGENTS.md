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

- **Entrypoint**: `main.py:app` — FastAPI instance; lifespan startup initialises Firebase, builds the NN index, and caches the activity→category map
- **Auth**: all protected routes use `src/dependencies.py:get_current_user` — verifies Firebase Bearer tokens, raises HTTP 401 on failure
- **Routers**: `src/routers/health.py` (public `GET /health`), `src/routers/recommendations.py` (auth-protected `GET /recommendations`)
- **ML index**: built at startup from Firestore `activities` collection (excluding `EXCLUDED_ACTIVITY_IDS`), stored at `app.state.nn_index`
- **Activity category cache**: `app.state.activity_categories: dict[str, str]` — maps activity doc_id → category slug, built at startup to avoid per-request Firestore reads during re-ranking
- **Models**: Pydantic schemas in `src/models/` — `category.py`, `user.py`, `recommendations.py`
- **Services**: business logic in `src/services/` — `user_vectors.py`, `recommendations.py`

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

Written directly by the Flutter client via the Firebase SDK.

```
onboardingComplete:  bool
preferences:
    features:    map    14 float keys matching activity weight keys (0.0–1.0, default 0.5)
        social, goal, energy_type, variety, intensity, strength, fitness,
        coordination, flexibility, contact, opponent, social_interaction,
        tactical, mental_calm
    categories:  map    10 float keys matching category slugs (0.0–1.0, default 0.5)
        team_sports, racket_sports, combat_sports, dance, fitness_strength,
        group_cardio, mind_body, individual_sports, outdoor_adventure, creative_cultural
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

The following activity doc IDs are present in the Firestore `activities` collection
(seeded for completeness) but are **excluded from the NN index** at startup:

- Meet & Play formats: `meet_and_play_beach_volleyball`, `meet_and_play_basketball`, `meet_and_play_volleyball`, `meet_and_play_tennis`, `beach_volleyball_meetplay`, `volleyball_meetplay`, `tennis_meetplay`
- Events/services: `internal_comp`, `fms_test`, `run_analysis`, `nutrition_advice`, `nutrition_advice_medical`, `culture`, `mental_sport`, `lecture`, `performance`, `workshop`, `spinning_movie`, `spinning_ftp`

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
