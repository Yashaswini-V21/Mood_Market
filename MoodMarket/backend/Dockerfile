FROM python:3.11

WORKDIR /app

# ── Context is ./MoodMarket (set in build.yml) ──────────────────────────────
# COPY paths are relative to ./MoodMarket

# Copy and install Python requirements first (layer-cache friendly)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./backend/

# Copy ML module so backend imports (agents, inference, etc.) resolve
COPY ml/ ./ml/

# Ensure both modules are on PYTHONPATH
ENV PYTHONPATH=/app/backend:/app/ml

WORKDIR /app/backend

# Expose FastAPI default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/api/v1/health || exit 1

# Run production server
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
