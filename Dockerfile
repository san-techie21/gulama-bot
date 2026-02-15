# Gulama Bot — Production Docker Image
# Multi-stage build with security hardening
#
# Usage:
#   docker build -t gulama .
#   docker run -d --name gulama -p 127.0.0.1:18789:18789 gulama
#
# Profiles:
#   docker compose up                     # Standard
#   docker compose --profile gpu up       # With GPU support
#   docker compose --profile full up      # All optional dependencies

FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only dependency files first for layer caching
COPY pyproject.toml ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[all-channels]"

# --- Production image ---
FROM python:3.12-slim AS production

LABEL maintainer="Santosh <santosh@astrafintechlabs.com>"
LABEL org.opencontainers.image.title="Gulama"
LABEL org.opencontainers.image.description="Secure personal AI agent"
LABEL org.opencontainers.image.url="https://gulama.ai"
LABEL org.opencontainers.image.source="https://github.com/san-techie21/gulama-bot"
LABEL org.opencontainers.image.licenses="MIT"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    bubblewrap \
    ca-certificates \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with specific UID/GID
RUN groupadd --gid 1000 gulama && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash gulama

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=gulama:gulama . .

# Create required directories with correct permissions
RUN mkdir -p /home/gulama/.gulama/audit \
             /home/gulama/.gulama/skills \
             /home/gulama/.gulama/logs \
             /home/gulama/.gulama/cache \
             /home/gulama/.gulama/chroma && \
    chown -R gulama:gulama /home/gulama/.gulama && \
    chown -R gulama:gulama /app

# Drop all capabilities, run as non-root
USER gulama

# Runtime configuration
ENV GULAMA_DEV=false \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GULAMA_DATA_DIR=/home/gulama/.gulama

# Health check using curl (lighter than importing httpx)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:18789/health || exit 1

# Expose gateway port
EXPOSE 18789

# Use tini as init system for proper signal handling
ENTRYPOINT ["tini", "--"]

# Start Gulama
CMD ["gulama", "start", "--no-browser"]
