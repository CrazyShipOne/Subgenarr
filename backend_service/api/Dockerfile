# API service Dockerfile for video subtitle generation

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy shared module first
COPY ../shared /app/shared

# Copy API requirements and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy API source code
COPY src /app/src

# Set Python path
ENV PYTHONPATH=/app:/app/src

# Create directories for volumes
RUN mkdir -p /config

# Environment variables (with defaults)
ENV DATABASE_PATH=/config/media_library.db
ENV CONFIG_DIR=/config

# Authentication (should be overridden in production)
ENV AUTH_USERNAME=admin
ENV AUTH_PASSWORD=admin
ENV SESSION_SECRET=change-me-in-production
ENV SESSION_EXPIRY=86400

# Network configuration
ENV BACKEND_PORT=8000

# Worker configuration (for status display)
ENV MAX_CONCURRENT_WORKERS=2

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run API service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
