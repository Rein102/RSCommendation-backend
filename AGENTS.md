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
- **Routers**: `src/routers/health.py` (public `GET /health`), `src/routers/recommendations.py` (auth-protected `POST /recommendations`)
- **ML index**: built at startup from placeholder vectors, stored at `app.state.nn_index` — real training vectors should replace the placeholders in `main.py:lifespan`
- **Models**: Pydantic schemas currently colocated in routers; new models belong in `src/models/`
- **Services/business logic**: add to `src/services/` (create the package when first needed)

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
