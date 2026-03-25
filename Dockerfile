# ── Stage 1: builder ─────────────────────────────────────────────────────────
# Install dependencies into a venv in an isolated layer so the final image
# only copies the venv, not build tools or cache.
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools needed by some Python packages (e.g. asyncpg C extension)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first — Docker layer cache means this layer is
# only rebuilt when dependencies change, not on every source code change.
COPY pyproject.toml .
COPY app/__init__.py app/__init__.py

# Create venv + install runtime deps + GCP extras for Secret Manager.
# We install the package itself in editable mode so app/ is importable.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -e ".[gcp]" --no-cache-dir

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Install only the runtime C libraries (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user — required for Cloud Run security best practices.
# Cloud Run runs as root by default; we override explicitly.
RUN groupadd --gid 1001 routersvc \
    && useradd --uid 1001 --gid routersvc --shell /bin/bash --no-create-home routersvc

WORKDIR /app

# Copy installed venv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source
COPY --chown=routersvc:routersvc app/ app/
COPY --chown=routersvc:routersvc alembic/ alembic/
COPY --chown=routersvc:routersvc alembic.ini alembic.ini
COPY --chown=routersvc:routersvc pyproject.toml pyproject.toml

# Make venv binaries available on PATH
ENV PATH="/opt/venv/bin:$PATH" \
    # Prevent Python from writing .pyc files into the image layer
    PYTHONDONTWRITEBYTECODE=1 \
    # Unbuffered stdout/stderr → structlog JSON lands in Cloud Logging immediately
    PYTHONUNBUFFERED=1

USER routersvc

# Cloud Run injects PORT (default 8080). We read it at runtime.
# --workers 1: Cloud Run scales horizontally; one worker per container is
#   the standard pattern. Increase only if CPU-bound work warrants it.
# --proxy-headers: trust X-Forwarded-For from Cloud Load Balancer.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
