"""BioSim AI REST API (skeleton: health + spec validation)."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .plan import router as plan_router
from .runs import engines_router, router as runs_router
from .tools import router as tools_router
from .validation import router as specs_router

app = FastAPI(title="BioSim AI API", version="0.1.0")
# Shrink ~400 KB trajectory payloads for phones on slow networks.
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def rate_limit_expensive_posts(request, call_next):
    """Backpressure before queueing solver/model work (HTTP 429 + Retry-After)."""
    from .ratelimit import bucket_for
    bucket = (bucket_for(request.url.path)
              if request.method == "POST" else None)
    if bucket is not None:
        ip = (request.client.host if request.client else "unknown")
        ok, retry_after = bucket.allow(f"{ip}:{request.url.path}")
        if not ok:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                {"code": "rate_limited",
                 "message": "too many requests: slow down and retry",
                 "retry_after_s": round(retry_after, 1)},
                status_code=429,
                headers={"Retry-After": str(max(1, int(retry_after + 0.5)))},
            )
    return await call_next(request)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get(
        "BIOSIM_CORS_ORIGINS", "http://localhost:5173,http://localhost:4173").split(",")],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["content-type"],
)
app.include_router(specs_router)
app.include_router(runs_router)
app.include_router(engines_router)
app.include_router(plan_router)
app.include_router(tools_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "biosim-api", "version": "0.1.0"}
