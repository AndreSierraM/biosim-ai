"""BioSim AI REST API (skeleton: health + spec validation)."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .plan import router as plan_router
from .runs import engines_router, router as runs_router
from .validation import router as specs_router

app = FastAPI(title="BioSim AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get(
        "BIOSIM_CORS_ORIGINS", "http://localhost:5173,http://localhost:4173").split(",")],
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)
app.include_router(specs_router)
app.include_router(runs_router)
app.include_router(engines_router)
app.include_router(plan_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "biosim-api", "version": "0.1.0"}
