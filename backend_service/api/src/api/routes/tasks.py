"""Task management API routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from sqlalchemy import and_

import sys
sys.path.append('/app/shared')

from shared import (
    get_db_session,
    MediaLibrary,
    TaskQueue,
    ProcessingHistory,
    TaskStatus,
    config,
)
from api.middleware.auth import get_current_user
from api.schemas import (
    TaskListResponse,
    TaskDetailResponse,
    TaskRetryResponse,
    TaskCancelResponse,
    TaskTriggerRequest,
    TaskTriggerResponse,
)

router = APIRouter(prefix="/tasks", tags=["Task Management"])


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    media_id: Optional[int] = None,
    media_type: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List all tasks with filtering and pagination."""
    try:
        with get_db_session() as session:
            # Base query
            query = session.query(TaskQueue, MediaLibrary).join(
                MediaLibrary, TaskQueue.media_id == MediaLibrary.media_id
            )

            # Apply filters
            if status_filter:
                try:
                    task_status = TaskStatus(status_filter)
                    query = query.filter(TaskQueue.status == task_status)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid status: {status_filter}"
                    )

            if media_id:
                query = query.filter(TaskQueue.media_id == media_id)

            if media_type:
                query = query.filter(MediaLibrary.media_type == media_type)

            # Get total count
            total_items = query.count()

            # Apply pagination
            offset = (page - 1) * page_size
            results = query.order_by(TaskQueue.created_at.asc()).offset(offset).limit(page_size).all()

            # Format response
            task_items = []
            for task, media in results:
                task_items.append({
                    "task_id": task.task_id,
                    "media_id": media.media_id,
                    "media_title": media.title,
                    "media_type": media.media_type.value,
                    "season": media.season,
                    "episode": media.episode,
                    "status": task.status.value,
                    "retry_count": task.retry_count,
                    "failure_reason": task.failure_reason,
                    "worker_assignment": task.worker_assignment,
                    "queued_time": task.queued_time.isoformat() if task.queued_time else None,
                    "started_time": task.started_time.isoformat() if task.started_time else None,
                    "timeout_deadline": task.timeout_deadline.isoformat() if task.timeout_deadline else None,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                })

            total_pages = (total_items + page_size - 1) // page_size

            return TaskListResponse(
                success=True,
                data={
                    "items": task_items,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_items": total_items,
                        "total_pages": total_pages,
                    }
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(
    task_id: int,
    user: dict = Depends(get_current_user)
):
    """Get detailed information for a specific task."""
    try:
        with get_db_session() as session:
            result = session.query(TaskQueue, MediaLibrary).join(
                MediaLibrary, TaskQueue.media_id == MediaLibrary.media_id
            ).filter(TaskQueue.task_id == task_id).first()

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )

            task, media = result

            data = {
                "task_id": task.task_id,
                "media_id": media.media_id,
                "media_title": media.title,
                "media_type": media.media_type.value,
                "nfo_file_path": task.nfo_file_path,
                "video_file_path": task.video_file_path,
                "status": task.status.value,
                "retry_count": task.retry_count,
                "failure_reason": task.failure_reason,
                "worker_assignment": task.worker_assignment,
                "queued_time": task.queued_time.isoformat() if task.queued_time else None,
                "started_time": task.started_time.isoformat() if task.started_time else None,
                "timeout_deadline": task.timeout_deadline.isoformat() if task.timeout_deadline else None,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }

            return TaskDetailResponse(success=True, data=data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{task_id}/retry", response_model=TaskRetryResponse)
async def retry_task(
    task_id: int,
    user: dict = Depends(get_current_user)
):
    """Retry a failed task."""
    try:
        with get_db_session() as session:
            task = session.query(TaskQueue).filter(TaskQueue.task_id == task_id).first()

            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )

            # Only failed tasks can be retried
            if task.status != TaskStatus.FAILED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task cannot be retried (status: {task.status.value})"
                )

            # Reset task for retry
            task.status = TaskStatus.PENDING
            task.failure_reason = None
            task.worker_assignment = None
            task.started_time = None
            task.timeout_deadline = None
            task.retry_count += 1
            task.updated_at = datetime.now(timezone.utc)

            session.commit()

            return TaskRetryResponse(
                success=True,
                message="Task queued for retry",
                data={
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "retry_count": task.retry_count,
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{task_id}/cancel", response_model=TaskCancelResponse)
async def cancel_task(
    task_id: int,
    user: dict = Depends(get_current_user)
):
    """Cancel a pending or processing task."""
    try:
        with get_db_session() as session:
            task = session.query(TaskQueue).filter(TaskQueue.task_id == task_id).first()

            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )

            # Only pending/processing tasks can be cancelled
            if task.status not in [TaskStatus.PENDING, TaskStatus.METADATA_FETCHING, TaskStatus.PROCESSING]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task cannot be cancelled (status: {task.status.value})"
                )

            # Mark as failed with cancellation reason
            task.status = TaskStatus.FAILED
            task.failure_reason = "cancelled_by_user"
            task.updated_at = datetime.now(timezone.utc)

            session.commit()

            return TaskCancelResponse(
                success=True,
                message="Task cancelled successfully",
                data={
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "failure_reason": task.failure_reason,
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/trigger", response_model=TaskTriggerResponse)
async def trigger_task(
    request: TaskTriggerRequest,
    user: dict = Depends(get_current_user)
):
    """Manually trigger processing for a specific media item."""
    try:
        with get_db_session() as session:
            # Check if media exists
            media = session.query(MediaLibrary).filter(
                MediaLibrary.media_id == request.media_id
            ).first()

            if not media:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Media not found"
                )

            # Check if already has subtitle
            if media.subtitle_file_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Media already has subtitle"
                )

            # Check if task already exists
            existing_task = session.query(TaskQueue).filter(
                TaskQueue.media_id == request.media_id
            ).first()

            if existing_task:
                return TaskTriggerResponse(
                    success=True,
                    message="Task already exists",
                    data={
                        "task_id": existing_task.task_id,
                        "media_id": request.media_id,
                        "status": existing_task.status.value,
                    }
                )

            # Create new task
            task = TaskQueue(
                media_id=request.media_id,
                nfo_file_path=media.nfo_file_path,
                video_file_path=media.video_file_path,
                status=TaskStatus.PENDING,
                retry_count=0,
            )
            session.add(task)
            session.commit()

            return TaskTriggerResponse(
                success=True,
                message="Task created successfully",
                data={
                    "task_id": task.task_id,
                    "media_id": request.media_id,
                    "status": task.status.value,
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
