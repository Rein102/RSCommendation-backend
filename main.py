"""
RSCommendation Backend — FastAPI entry point.

Run locally (outside Docker):
    uvicorn main:app --reload --port 8000

Run via Docker Compose:
    docker compose up
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.firebase import get_app, get_db
from src.ml.nearest_neighbor import build_index
from src.routers import health, recommendations

load_dotenv()


# ---------------------------------------------------------------------------
# Activity IDs excluded from the NN index.
#
# These are services, assessments, event formats, or meet-and-play variants
# that are not meaningfully recommendable as regular activities.
# ---------------------------------------------------------------------------

EXCLUDED_ACTIVITY_IDS: frozenset[str] = frozenset({
    # Meet & Play event formats
    "meet_and_play_beach_volleyball",
    "meet_and_play_basketball",
    "meet_and_play_volleyball",
    "meet_and_play_tennis",
    "beach_volleyball_meetplay",
    "volleyball_meetplay",
    "tennis_meetplay",
    # Internal competition event
    "internal_comp",
    # Assessment & advisory services
    "fms_test",
    "run_analysis",
    "nutrition_advice",
    "nutrition_advice_medical",
    # Generic cultural/coaching umbrella entries (not specific activities)
    "culture",
    "mental_sport",
    # One-off events
    "lecture",
    "performance",
    "workshop",
    "spinning_movie",
    "spinning_ftp",
})

# Canonical order of the 14 taxonomy feature keys.
WEIGHT_KEYS: list[str] = [
    "social", "goal", "energy_type", "variety",
    "intensity", "strength", "fitness", "coordination", "flexibility",
    "contact", "opponent", "social_interaction", "tactical", "mental_calm",
]


# ---------------------------------------------------------------------------
# Lifespan: runs once on startup and once on shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # --- Startup ---

    # 1. Initialise Firebase / Firestore
    get_app()
    app.state.db = get_db()

    # 2. Stream all activity documents from Firestore.
    docs = list(app.state.db.collection("activities").stream())

    # 3. Filter: must have a weights map and must not be an excluded ID.
    valid_docs = [
        d for d in docs
        if d.to_dict().get("weights") and d.id not in EXCLUDED_ACTIVITY_IDS
    ]

    # 4. Build an in-memory category lookup: doc_id → category slug.
    #    Used at recommendation time to apply the category preference boost
    #    without additional Firestore reads.
    app.state.activity_categories: dict[str, str] = {
        d.id: d.to_dict()["category"]
        for d in valid_docs
        if d.to_dict().get("category")
    }

    # 5. Build the nearest-neighbour index from the valid activity vectors.
    if valid_docs:
        vectors = np.array(
            [
                [d.to_dict()["weights"].get(k, 0.5) for k in WEIGHT_KEYS]
                for d in valid_docs
            ],
            dtype=np.float32,
        )
        item_ids = [d.id for d in valid_docs]
        print(f"[startup] Loaded {len(item_ids)} activities into the NN index.")
    else:
        print("[startup] WARNING: No activities found in Firestore. Index not fitted.")
        vectors = np.empty((0, len(WEIGHT_KEYS)), dtype=np.float32)
        item_ids = []

    app.state.nn_index = build_index(vectors, item_ids)

    yield

    # --- Shutdown ---
    # Nothing to clean up for now.


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RSCommendation API",
    description="Radboud Sport & Culture recommendation backend.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins for development.
# Restrict `allow_origins` to specific domains before going to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(recommendations.router)
