# ─────────────────────────────────────────────────────────────────
# HangarLinks — Production Dockerfile
# ─────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# System packages required by WeasyPrint / Cairo / Pango
RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc \
  libpango-1.0-0 \
  libpangoft2-1.0-0 \
  libgdk-pixbuf-2.0-0 \
  libcairo2 \
  libffi-dev \
  zlib1g \
  libjpeg-dev \
  libgobject-2.0-0 \
  curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install Python deps into a virtual env
COPY requirements.txt .
RUN python -m venv /venv \
  && /venv/bin/pip install --upgrade pip \
  && /venv/bin/pip install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime — lean final image ───────────────────────────
FROM python:3.12-slim AS runtime

# Runtime libraries required by WeasyPrint and other components
RUN apt-get update && apt-get install -y --no-install-recommends \
  libpango-1.0-0 \
  libpangoft2-1.0-0 \
  libgdk-pixbuf-2.0-0 \
  libcairo2 \
  libgobject-2.0-0 \
  libjpeg62-turbo \
  libfontconfig1 \
  libharfbuzz0b \
  libfribidi0 \
  shared-mime-info \
  zlib1g \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN useradd --create-home --shell /bin/bash hangar
USER hangar

WORKDIR /app

# Copy the venv from builder
COPY --from=builder /venv /venv

# Copy application code
COPY --chown=hangar:hangar . .

# Environment variables
ENV PATH="/venv/bin:$PATH" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  FLASK_ENV=production

# Expose port (Railway injects $PORT)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start the application
CMD gunicorn \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  app:app
