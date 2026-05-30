# ─────────────────────────────────────────────────────────────────────────────
# EpitopX AI — Backend Dockerfile
# Multi-stage build:  builder (compile deps) → runtime (lean image)
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps needed to compile Python packages (psycopg2, argon2-cffi, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a dedicated prefix to copy into the runtime image
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: run as non-root
RUN groupadd --gid 1001 epitopx \
 && useradd  --uid 1001 --gid epitopx --shell /bin/bash --create-home epitopx

WORKDIR /app

# Runtime system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libffi8 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=epitopx:epitopx . .

# Create directories the app writes to
RUN mkdir -p /app/staticfiles /app/media \
 && chown -R epitopx:epitopx /app/staticfiles /app/media

USER epitopx

# Collect static files at build time (requires SECRET_KEY env var)
ARG SECRET_KEY=build-time-dummy-key
ARG DJANGO_DEBUG=False
ENV SECRET_KEY=${SECRET_KEY} \
    DJANGO_DEBUG=${DJANGO_DEBUG} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Healthcheck — lightweight Django check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health/')" || exit 1

# Gunicorn for production (Linux/Render)
CMD ["gunicorn", \
     "--bind",            "0.0.0.0:8000", \
     "--workers",         "4", \
     "--worker-class",    "sync", \
     "--threads",         "2", \
     "--timeout",         "120", \
     "--keep-alive",      "5", \
     "--access-logfile",  "-", \
     "--error-logfile",   "-", \
     "config.wsgi:application"]
