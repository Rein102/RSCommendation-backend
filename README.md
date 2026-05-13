# RSCommendation Backend

FastAPI backend for the Radboud Sport & Culture recommendation app. Returns personalised activity recommendations to authenticated Flutter clients via two complementary approaches: content-based filtering and collaborative filtering.

---

## Stack

Python 3.12, FastAPI, Uvicorn, Firebase Admin SDK, Firestore, scikit-learn, numpy, pandas. Package manager: `uv`.

---

## Quick start

```bash
# Install dependencies
uv sync

# Run locally (requires .env and GCP credentials — see Environment setup)
uvicorn main:app --reload --port 8000

# Or via Docker Compose (preferred)
docker compose up
```

---

## Environment setup

Copy `.env` and fill in the required values (ask the team). The file must contain at minimum:

```
ENVIRONMENT=development
GOOGLE_CLOUD_PROJECT=rscommendation-493408
GOOGLE_APPLICATION_CREDENTIALS=<path to ADC JSON>
```

GCP Application Default Credentials are required:

```bash
gcloud auth application-default login
```

Docker Compose mounts ADC automatically via the path in `.env`.

---

## First-time Firestore seeding

Run once. These scripts are idempotent.

```bash
python tools/seed_categories.py
python tools/seed_activities.py
```

---

## Recommendation system

### Content-based (`GET /recommendations`)

At startup the backend streams all activity documents from Firestore, builds a nearest-neighbour index over their 14-dim weight vectors, and caches it. When a user requests recommendations, their onboarding preference profile (also 14-dim, stored in Firestore) is compared to every activity via cosine similarity. Results are re-ranked using a soft category preference boost before the top-k are returned.

### Collaborative (`GET /recommendations/collaborative`)

Finds historical RSC members whose activity-derived profile is closest to the app user's profile, then recommends activities those members attended that the user has not tried yet.

This requires a one-time training step using historical attendance data from the RSC delta CSV files. After running the training script, the backend loads the resulting artifacts at startup and uses them to power a second NN index over historical member profiles.

#### Running the training script

Connect to the RSC network drive, then:

```bash
python tools/build_historical_profiles.py

# Override the data root if needed:
python tools/build_historical_profiles.py --data-root "\\ru.nl\WrkGrp\STD-RSC-NML\Delta-datafiles"

# Or set DELTA_DATA_ROOT in your .env file.
```

This writes three files to `model_artifacts/`:

| File | Contents |
|---|---|
| `historical_user_vectors.npy` | float32 array (n_users, 14) — one profile per historical member |
| `historical_user_activities.json` | list of activity doc ID lists, one per member in matching row order |

No user identifiers are stored. Row position is the only link between a profile vector and its activity list.

After training, restart the server. The startup log confirms how many users were loaded. If the files are absent, `GET /recommendations/collaborative` returns 503.

---

## API endpoints

All endpoints except `/health` require a Firebase ID token in the `Authorization: Bearer <token>` header.

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Public health check |
| GET | `/recommendations` | Content-based recommendations (k, default 10) |
| GET | `/recommendations/collaborative` | Collaborative recommendations (k, default 10) |

---

## Adding dependencies

```bash
uv add <package-name>
uv sync
```

Never use `pip install` directly. The `.venv/` is managed by `uv` and mounted as a named volume in Docker.

---

## Code layout

| Path | Purpose |
|---|---|
| `main.py` | FastAPI app, lifespan startup (indexes, artifacts) |
| `src/config.py` | Shared constants: `WEIGHT_KEYS`, `EXCLUDED_ACTIVITY_IDS` |
| `src/dependencies.py` | Firebase token verification dependency |
| `src/firebase.py` | Firebase Admin SDK initialisation |
| `src/ml/nearest_neighbor.py` | `NearestNeighborIndex` wrapper around scikit-learn |
| `src/models/` | Pydantic schemas |
| `src/routers/` | Route handlers |
| `src/services/recommendations.py` | Content-based recommendation logic |
| `src/services/collaborative_recommendations.py` | Collaborative recommendation logic |
| `src/services/user_vectors.py` | Firestore user data helpers |
| `tools/seed_categories.py` | Seed Firestore categories collection |
| `tools/seed_activities.py` | Seed Firestore activities collection |
| `tools/build_historical_profiles.py` | Build collaborative model artifacts from delta CSVs |
| `model_artifacts/` | Generated artifacts (gitignored, loaded at startup) |
