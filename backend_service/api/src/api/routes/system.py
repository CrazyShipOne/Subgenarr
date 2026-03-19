"""System status API routes."""

import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy import text
from typing import Optional

import sys
sys.path.append('/app/shared')

from shared import (
    get_db_session,
    MediaLibrary,
    TaskQueue,
    TaskStatus,
    ExistenceStatus,
    engine,
    config,
)
from api.middleware.auth import get_current_user
from api.schemas import HealthResponse, SystemStatusResponse

router = APIRouter(tags=["System Status"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    now = datetime.now(timezone.utc)
    services = {}
    all_healthy = True

    # Check database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        services["database"] = "healthy"
    except Exception as e:
        services["database"] = "unhealthy"
        all_healthy = False

    # Check worker (simplified - just check if database is accessible)
    services["worker"] = "healthy" if services["database"] == "healthy" else "unhealthy"

    if all_healthy:
        return HealthResponse(
            status="healthy",
            timestamp=now,
            services=services
        )
    else:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=HealthResponse(
                status="unhealthy",
                timestamp=now,
                services=services,
                error="One or more services are unhealthy"
            ).dict()
        )


@router.get("/status", response_model=SystemStatusResponse)
async def system_status(user: dict = Depends(get_current_user)):
    """Get system status and statistics."""
    try:
        with get_db_session() as session:
            # Queue statistics
            queue_stats = {
                "pending": session.query(TaskQueue).filter(TaskQueue.status == TaskStatus.PENDING).count(),
                "metadata_fetching": session.query(TaskQueue).filter(TaskQueue.status == TaskStatus.METADATA_FETCHING).count(),
                "processing": session.query(TaskQueue).filter(TaskQueue.status == TaskStatus.PROCESSING).count(),
                "failed": session.query(TaskQueue).filter(TaskQueue.status == TaskStatus.FAILED).count(),
            }
            queue_stats["total"] = sum(queue_stats.values())

            # Worker information (from processing tasks)
            processing_tasks = session.query(TaskQueue).filter(
                TaskQueue.status == TaskStatus.PROCESSING
            ).all()

            workers = []
            for task in processing_tasks:
                if task.worker_assignment:
                    workers.append({
                        "worker_id": task.worker_assignment,
                        "status": "busy",
                        "current_task_id": task.task_id,
                        "started_at": task.started_time.isoformat() if task.started_time else None,
                    })

            worker_info = {
                "max_concurrent": config.MAX_CONCURRENT_WORKERS,
                "active": len(workers),
                "workers": workers,
            }

            # Media statistics
            total_media = session.query(MediaLibrary).filter(
                MediaLibrary.existence_status == ExistenceStatus.EXISTS
            ).count()

            movies_count = session.query(MediaLibrary).filter(
                MediaLibrary.media_type == "movie",
                MediaLibrary.existence_status == ExistenceStatus.EXISTS
            ).count()

            tv_episodes_count = session.query(MediaLibrary).filter(
                MediaLibrary.media_type == "tv",
                MediaLibrary.existence_status == ExistenceStatus.EXISTS
            ).count()

            with_subtitles = session.query(MediaLibrary).filter(
                MediaLibrary.existence_status == ExistenceStatus.EXISTS,
                MediaLibrary.subtitle_file_path.isnot(None)
            ).count()

            without_subtitles = total_media - with_subtitles

            media_stats = {
                "total": total_media,
                "movies": movies_count,
                "tv_episodes": tv_episodes_count,
                "with_subtitles": with_subtitles,
                "without_subtitles": without_subtitles,
            }

            # Storage statistics
            temp_usage_mb = 0
            if os.path.exists(config.TEMP_DIR):
                try:
                    for dirpath, dirnames, filenames in os.walk(config.TEMP_DIR):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            temp_usage_mb += os.path.getsize(filepath)
                    temp_usage_mb = temp_usage_mb // (1024 * 1024)  # Convert to MB
                except:
                    temp_usage_mb = 0

            database_size_mb = 0
            if os.path.exists(config.DATABASE_PATH):
                try:
                    database_size_mb = os.path.getsize(config.DATABASE_PATH) // (1024 * 1024)
                except:
                    database_size_mb = 0

            storage_stats = {
                "temp_directory": config.TEMP_DIR,
                "temp_usage_mb": temp_usage_mb,
                "database_size_mb": database_size_mb,
            }

            # System information
            # Note: uptime tracking would require storing start time somewhere
            system_info = {
                "version": "1.0.0",
                "uptime_seconds": 0,  # Placeholder
                "current_time": datetime.now(timezone.utc).isoformat(),
            }

            return SystemStatusResponse(
                success=True,
                data={
                    "system": system_info,
                    "queue": queue_stats,
                    "workers": worker_info,
                    "media": media_stats,
                    "storage": storage_stats,
                }
            )

    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
