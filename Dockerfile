# Unified production image: FastAPI serves the built React app directly
# (single origin, no CORS/proxy setup needed for the browser) plus the API
# under /api and uploaded files under /uploads. Build context is the repo
# root so this stage can reach both backend/ and frontend/.
#
# The ARQ worker uses backend/Dockerfile instead (no frontend needed there).

# --- stage 1: build the React app ---
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# --- stage 2: compile backend wheels ---
FROM python:3.12-slim AS backend-builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# --- stage 3: runtime ---
FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=backend-builder /wheels /wheels
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY backend/ .
COPY --from=frontend-builder /frontend/dist ./static

RUN mkdir -p uploads && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# --proxy-headers + --forwarded-allow-ips='*': the container only ever sees
# traffic through the platform's reverse proxy (Docker/Railway), so trust
# its X-Forwarded-For for the real client IP — otherwise every request
# looks like it's from the proxy, and the login rate limiter would count
# every user's attempts together.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
