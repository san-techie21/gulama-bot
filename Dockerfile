# Gulama Bot — Docker Image
# Multi-stage build for minimal image size

FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# --- Production image ---
FROM python:3.12-slim

# Install runtime dependencies (bubblewrap for sandboxing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    bubblewrap \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash gulama

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /home/gulama/.gulama && \
    chown -R gulama:gulama /home/gulama/.gulama && \
    chown -R gulama:gulama /app

USER gulama

# Default configuration
ENV GULAMA_DEV=false
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import httpx; httpx.get('http://127.0.0.1:18789/health')" || exit 1

# Expose gateway port (loopback only by default)
EXPOSE 18789

# Start Gulama
ENTRYPOINT ["gulama"]
CMD ["start", "--no-browser"]
