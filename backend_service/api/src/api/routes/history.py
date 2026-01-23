"""Processing history API routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from datetime import datetime
from sqlalchemy import and_, func
from collections import defaultdict

import sys
sys.path.append('/app/shared')

from shared import (
    get_db_session,
    MediaLibrary,
    ProcessingHistory,
    HistoryStatus,
)
from api.middleware.auth import get_current_user
from api.schemas import HistoryListResponse, HistoryStatsResponse

router = APIRouter(prefix="/history", tags=["Processing History"])


@router.get("", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    media_id: Optional[int] = None,
    media_type: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List processing history with filtering and pagination."""
    try:
        with get_db_session() as session:
            # Base query
            query = session.query(ProcessingHistory, MediaLibrary).join(
                MediaLibrary, ProcessingHistory.media_id == MediaLibrary.media_id
            )

            # Apply filters
            if status_filter:
                try:
                    history_status = HistoryStatus(status_filter)
                    query = query.filter(ProcessingHistory.status == history_status)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid status: {status_filter}"
                    )

            if media_id:
                query = query.filter(ProcessingHistory.media_id == media_id)

            if media_type:
                query = query.filter(MediaLibrary.media_type == media_type)

            if search:
                query = query.filter(MediaLibrary.title.ilike(f"%{search}%"))

            if date_from:
                try:
                    date_from_dt = datetime.fromisoformat(date_from)
                    query = query.filter(ProcessingHistory.created_at >= date_from_dt)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid date_from format: {date_from}"
                    )

            if date_to:
                try:
                    date_to_dt = datetime.fromisoformat(date_to)
                    query = query.filter(ProcessingHistory.created_at <= date_to_dt)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid date_to format: {date_to}"
                    )

            # Get total count
            total_items = query.count()

            # Apply pagination
            offset = (page - 1) * page_size
            results = query.order_by(ProcessingHistory.created_at.desc()).offset(offset).limit(page_size).all()

            # Format response
            history_items = []
            for history, media in results:
                history_items.append({
                    "history_id": history.history_id,
                    "task_id": history.task_id,
                    "media_id": media.media_id,
                    "media_title": media.title,
                    "media_type": media.media_type.value,
                    "season": media.season,
                    "episode": media.episode,
                    "status": history.status.value,
                    "processing_duration_seconds": history.processing_duration_seconds,
                    "failure_reason": history.failure_reason,
                    "error_details": history.error_details,
                    "created_at": history.created_at.isoformat(),
                })

            total_pages = (total_items + page_size - 1) // page_size

            return HistoryListResponse(
                success=True,
                data={
                    "items": history_items,
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


@router.get("/stats", response_model=HistoryStatsResponse)
async def get_history_stats(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get processing statistics."""
    try:
        with get_db_session() as session:
            # Base query
            query = session.query(ProcessingHistory)

            # Apply date filters
            if date_from:
                try:
                    date_from_dt = datetime.fromisoformat(date_from)
                    query = query.filter(ProcessingHistory.created_at >= date_from_dt)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid date_from format: {date_from}"
                    )

            if date_to:
                try:
                    date_to_dt = datetime.fromisoformat(date_to)
                    query = query.filter(ProcessingHistory.created_at <= date_to_dt)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid date_to format: {date_to}"
                    )

            # Get all records
            all_records = query.all()

            # Calculate statistics
            total_processed = len(all_records)
            successful = sum(1 for r in all_records if r.status == HistoryStatus.SUCCESS)
            failed = sum(1 for r in all_records if r.status == HistoryStatus.FAILED)
            success_rate = successful / total_processed if total_processed > 0 else 0.0

            # Calculate duration statistics
            durations = [r.processing_duration_seconds for r in all_records if r.processing_duration_seconds]
            average_duration = sum(durations) / len(durations) if durations else 0
            total_duration = sum(durations) if durations else 0

            # Failure reasons breakdown
            failure_reasons = defaultdict(int)
            for record in all_records:
                if record.status == HistoryStatus.FAILED and record.failure_reason:
                    failure_reasons[record.failure_reason] += 1

            # Processing by date
            processing_by_date_dict = defaultdict(lambda: {"total": 0, "successful": 0, "failed": 0})
            for record in all_records:
                date_key = record.created_at.date().isoformat()
                processing_by_date_dict[date_key]["total"] += 1
                if record.status == HistoryStatus.SUCCESS:
                    processing_by_date_dict[date_key]["successful"] += 1
                else:
                    processing_by_date_dict[date_key]["failed"] += 1

            # Convert to list and sort by date
            processing_by_date = [
                {"date": date_key, **stats}
                for date_key, stats in sorted(processing_by_date_dict.items())
            ]

            return HistoryStatsResponse(
                success=True,
                data={
                    "total_processed": total_processed,
                    "successful": successful,
                    "failed": failed,
                    "success_rate": success_rate,
                    "average_duration_seconds": int(average_duration),
                    "total_duration_seconds": total_duration,
                    "failure_reasons": dict(failure_reasons),
                    "processing_by_date": processing_by_date,
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
