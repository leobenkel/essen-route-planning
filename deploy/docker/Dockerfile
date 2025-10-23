# Multi-stage build for Essen Route Planning API
FROM python:3.13-slim AS builder

# Set working directory
WORKDIR /build

# Copy requirements and install dependencies
COPY src/api/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user for production (UID 1000 to match common host user)
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g 1000 -m -s /bin/bash appuser

# Copy installed packages from builder to appuser's local directory
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Make sure scripts in appuser's .local are usable
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy source code and set ownership
COPY --chown=appuser:appuser src/ ./src/

# Copy Essen data files to initial-data (not /app/data since PVC will mount there)
COPY --chown=appuser:appuser data/output/ /app/initial-data/

# Copy entrypoint script
COPY --chown=appuser:appuser deploy/docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create data directories (will be overridden by PVC mount in production)
RUN mkdir -p /app/data/cache /app/data/output && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check using curl instead of Python requests to avoid event loop conflicts
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application via entrypoint script (handles data initialization)
CMD ["/app/entrypoint.sh"]
