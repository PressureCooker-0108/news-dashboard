# ──────────────────────────────────────────────
# News Dashboard — Backend Dockerfile
# ──────────────────────────────────────────────
# Build:
#   docker build -t news-backend -f backend/Dockerfile backend/
#
# Run:
#   docker run -p 8001:8001 \
#     -e DATABASE_URL=postgresql://... \
#     -e API_KEY=your-secret-key \
#     -e CORS_ORIGINS=https://your-frontend.com \
#     news-backend
# ──────────────────────────────────────────────

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (kept as fallback)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (cached layer)
# --only-binary :all: forces pre-compiled wheels — avoids 10+ min compilation
# of hdbscan/scikit-learn on Render's limited CPU. Falls back to source build
# if a wheel isn't available (unlikely on Linux amd64).
COPY requirements.txt .
RUN pip install --no-cache-dir --user --only-binary :all: -r requirements.txt || \
    pip install --no-cache-dir --user -r requirements.txt


# ── Runtime stage ────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Ensure local binaries are on PATH
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY . .

# Health check — hits the / endpoint which no longer touches the database.
# Uses sh -c so $PORT expands correctly (Render sets PORT).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8001}/')" || exit 1

EXPOSE 8001

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"]
