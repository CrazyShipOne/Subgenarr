# Worker service Dockerfile for video subtitle generation

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy shared module first
COPY shared /app/shared

# Copy worker requirements and install
COPY worker/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker source code
COPY worker/src /app/src

# Set Python path
ENV PYTHONPATH=/app:/app/src

# Create directories for volumes
RUN mkdir -p /media /tmp /config

# Environment variables (with defaults)
ENV WORKER_ID=worker-1
ENV DATABASE_PATH=/config/media_library.db
ENV MEDIA_DIR=/media
ENV TEMP_DIR=/tmp
ENV CONFIG_DIR=/config

# Worker configuration
ENV MAX_CONCURRENT_WORKERS=2
ENV WORKER_POLL_INTERVAL=30
ENV TASK_TIMEOUT=7200

# Processing configuration
ENV AUDIO_SEGMENT_DURATION=300
ENV AUDIO_OVERLAP_DURATION=10
ENV SCREENSHOTS_PER_SEGMENT=10
ENV TARGET_SUBTITLE_LANGUAGE=en
ENV TEMP_CLEANUP_ENABLED=true
ENV TEMP_RETENTION_HOURS=24

# AI configuration (to be provided at runtime)
ENV AI_BASE_URL=https://api.openai.com/v1
ENV AI_MODEL=gpt-4o
ENV AI_TIMEOUT=300
ENV AI_MAX_RETRIES=3

# Metadata API configuration (optional)
ENV METADATA_API_TIMEOUT=30

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.path.append('/app/shared'); from shared import engine; engine.connect()" || exit 1

# Run worker service
CMD ["python", "-m", "worker.main"]
