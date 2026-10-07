"""Cafe Finder read API.

Thin HTTP adapter over the ``cafe_finder`` domain package. All search,
distance, ranking, quality, and analytics behavior lives in
``src/cafe_finder/``; this application only validates queries,
calls those functions, and serializes their outputs.
"""

import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import cafe_finder
from cafe_finder.config import DEFAULT_CSV_PATH

from .dependencies import load_dataset
from .routes import analytics, cafes, history, integrity, lineage, quality
from .schemas import DatasetInfo, HealthResponse

logger = logging.getLogger("cafe_finder.api")


def _allowed_origins() -> list[str]:
    """CORS origins from the environment, defaulting to local Vite dev."""
    raw = os.environ.get("CAFE_FINDER_CORS_ORIGINS", "")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins:
        origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    return origins


app = FastAPI(title="Cafe Finder API", version=cafe_finder.__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log method, path, and status only — never bodies or environment."""
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "%s %s -> %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError):
    """Never expose filesystem paths for missing data files."""
    return JSONResponse(status_code=500, content={"detail": "Dataset unavailable"})


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report API liveness and local dataset availability.

    Checks only local application state: no database, no Overpass, and
    no network access are involved.
    """
    csv_path = DEFAULT_CSV_PATH
    if not csv_path.exists():
        return HealthResponse(
            status="ok",
            app="cafe-finder",
            version=cafe_finder.__version__,
            dataset=DatasetInfo(available=False, records=0),
        )
    df = load_dataset()
    return HealthResponse(
        status="ok",
        app="cafe-finder",
        version=cafe_finder.__version__,
        dataset=DatasetInfo(available=True, records=len(df)),
    )


app.include_router(cafes.router, prefix="/api", tags=["cafes"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(quality.router, prefix="/api", tags=["quality"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(integrity.router, prefix="/api", tags=["integrity"])
app.include_router(lineage.router, prefix="/api", tags=["lineage"])
