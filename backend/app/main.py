import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import from_url as redis_from_url
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.db import engine
from app.core.exceptions import AppError, AuthError, ConflictError, NotFoundError, ValidationError
from app.core.logging import configure_logging, log_request
from app.core.rate_limit import limiter

configure_logging()
logger = logging.getLogger("app")

Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0")

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    log_request(logger, request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    # Defense in depth: nginx sets these too, but the backend's Railway URL
    # can be reached directly, not just through the frontend's proxy.
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Too many requests, please try again shortly"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

_ERROR_STATUS_MAP = {
    NotFoundError: 404,
    ConflictError: 409,
    ValidationError: 422,
    AuthError: 401,
}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    status_code = _ERROR_STATUS_MAP.get(type(exc), 400)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict:
    """Liveness probe: process is up and serving. Deliberately does not
    touch the DB/Redis so a brief dependency hiccup doesn't flap the
    container health status — see /health/ready for that."""
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> JSONResponse:
    """Readiness probe: verifies the app can actually reach Postgres and
    Redis. Useful for deploy-time smoke checks, not the container's own
    restart-on-failure healthcheck (that stays on /health)."""
    checks: dict[str, str] = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - report any failure, don't crash the probe
        checks["database"] = f"error: {exc}"

    try:
        redis_client = redis_from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await redis_client.ping()
        await redis_client.aclose()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc}"

    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )


# --- unified-origin frontend serving ---
#
# The production image copies the built React app into ./static (see the
# root Dockerfile). This route is registered last, so it only ever fires
# for requests that didn't match /api/*, /uploads/*, /health*, or the
# OpenAPI docs above — everything else either maps to a real built file
# (JS/CSS chunks, manifest, service worker, icons) or falls back to
# index.html so React Router can handle the path client-side.
#
# In local dev (docker-compose.dev.yml), FRONTEND_DIST doesn't exist —
# the frontend runs on its own Vite dev server instead — so this block is
# skipped entirely and requests for unknown paths just 404 from FastAPI,
# which is correct there since nothing is being served at this origin.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "static"

if FRONTEND_DIST.is_dir():

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str) -> FileResponse:
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
