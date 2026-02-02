# Multi-stage production build for FastAPI backend
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Set working directory
WORKDIR /app

# Copy dependency files from backend directory
COPY backend/pyproject.toml backend/README.md ./

# Install dependencies using uv (production only, no lock file)
RUN uv sync --no-dev

# Production stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser appuser

# Copy uv and installed packages from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=builder /app/.venv /app/.venv

# Ensure scripts in .venv are usable
ENV PATH="/app/.venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code from backend/
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./

# Create necessary directories
RUN mkdir -p /app/logs /app/config && \
    chown -R appuser:appuser /app

# Copy entrypoint script
COPY deploy/scripts/entrypoint-backend.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Set entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]

# Run uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
