# ---------------------------------------------------------------------------
# Stage 1: dependency resolution
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency manifests first (layer-cache friendly)
COPY pyproject.toml uv.lock ./

# Sync dependencies into a virtual environment inside the image
RUN uv sync --frozen --no-dev

# ---------------------------------------------------------------------------
# Stage 2: runtime image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy the pre-built venv from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY main.py ./
COPY src/ ./src/

# Make the venv the active Python environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose the application port
EXPOSE 8000

# Production command (no --reload)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
