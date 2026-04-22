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
# Lifespan: runs once on startup and once on shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # --- Startup ---

    # 1. Initialise Firebase / Firestore
    get_app()
    app.state.db = get_db()

    # 2. Build the nearest-neighbour index from the Firestore `activities` collection.
    #    Each document must have a `weights` map with the 14 taxonomy keys in order:
    #    social, goal, energy_type, variety, intensity, strength, fitness,
    #    coordination, flexibility, contact, opponent, social_interaction,
    #    tactical, mental_calm
    WEIGHT_KEYS = [
        "social", "goal", "energy_type", "variety",
        "intensity", "strength", "fitness", "coordination", "flexibility",
        "contact", "opponent", "social_interaction", "tactical", "mental_calm",
    ]

    docs = list(app.state.db.collection("activities").stream())
    valid_docs = [d for d in docs if d.to_dict().get("weights")]

    if valid_docs:
        vectors = np.array(
            [[d.to_dict()["weights"].get(k, 0.5) for k in WEIGHT_KEYS] for d in valid_docs],
            dtype=np.float32,
        )
        item_ids = [d.id for d in valid_docs]
        print(f"[startup] Loaded {len(item_ids)} activities from Firestore.")
    else:
        # Fallback: empty index (will return 503 on query — better than random data)
        print("[startup] WARNING: No activities found in Firestore. Index not fitted.")
        vectors = np.empty((0, len(WEIGHT_KEYS)), dtype=np.float32)
        item_ids = []

    app.state.nn_index = build_index(vectors, item_ids)

    yield

    # --- Shutdown ---
    # Nothing to clean up for now; add teardown logic here if needed.


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
