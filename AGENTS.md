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
```

## Environment setup

- Requires a `.env` file at the repo root (not committed — check with the team for required keys)
- Requires GCP Application Default Credentials at `~/.config/gcloud/application_default_credentials.json`
- Firebase project: `rscommendation-493408`
- `compose.yaml` mounts ADC and sets `GOOGLE_APPLICATION_CREDENTIALS` automatically for Docker runs

## Architecture

- **Entrypoint**: `main.py:app` — FastAPI instance; lifespan startup initialises Firebase and builds the NN index
- **Auth**: all protected routes use `src/dependencies.py:get_current_user` — verifies Firebase Bearer tokens, raises HTTP 401 on failure
- **Routers**: `src/routers/health.py` (public `GET /health`), `src/routers/recommendations.py` (auth-protected `GET /recommendations`)
- **ML index**: built at startup from activity vectors, stored at `app.state.nn_index` — loaded from Firestore `activities` collection, each document must have a `weights` map with the 14 taxonomy keys in order
- **Models**: Pydantic schemas currently colocated in routers; new models belong in `src/models/`
- **Services/business logic**: add to `src/services/` (create the package when first needed)

## Recommendation System

### Request Flow

1. Client sends `GET /recommendations` with Firebase ID token in `Authorization: Bearer <token>` header
2. Backend extracts authenticated user's UID from the verified Firebase token (via `src/dependencies.py:get_current_user`)
3. Fetches user preferences from Firestore (`users` collection, document ID = user UID)
4. Builds 14-dimensional preference vector using `src/services/user_vectors.py:get_user_vector()`:
   - For each of the 14 taxonomy categories, fetches the user's preference value
   - Missing categories default to `0.5`
5. Queries the NN index with `k=10` to find 10 nearest activity matches
6. Returns ordered list of activity IDs + authenticated user's UID

### Firestore Schema (Users)

**Collection**: `users`  
**Document ID**: Firebase user UID  
**Required field**:
- `preferences` (map): Keys are taxonomy category names, values are user preference floats (typically 0.0–1.0)

**Taxonomy Categories** (14 total, in order):
```
social, goal, energy_type, variety, intensity, strength, fitness,
coordination, flexibility, contact, opponent, social_interaction,
tactical, mental_calm
```

**Example user document**:
```json
{
  "preferences": {
    "social": 0.8,
    "intensity": 0.3,
    "tactical": 0.6
  }
}
```
Missing categories (e.g., `goal`, `fitness`, etc.) default to `0.5` when building the query vector.

### Services

- `src/services/user_vectors.py:get_user_vector(db, user_id: str) -> list[float]` — Fetches user preferences from Firestore and builds a 14-dimensional vector. Missing categories default to `0.5`. Raises `HTTPException(404)` if user document not found.

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
