"""Task processor for handling video subtitle generation tasks."""

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict

from sqlalchemy import and_
from sqlalchemy.orm import Session

import sys
sys.path.append('/app/shared')

from shared import (
    get_db_session,
    TaskQueue,
    MediaLibrary,
    ProcessingHistory,
    TaskStatus,
    HistoryStatus,
    ExistenceStatus,
    config,
)
from .metadata_enrichment import MetadataEnricher
from .media_processor import MediaProcessor

logger = logging.getLogger(__name__)


class TaskProcessor:
    """Handles task acquisition and processing coordination."""

    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.metadata_enricher = MetadataEnricher()
        self.media_processor = MediaProcessor()

    async def acquire_next_task(self) -> Optional[Dict]:
        """
        Acquire the next available task from the queue.

        Returns:
            Task dictionary if found, None otherwise.
        """
        try:
            with get_db_session() as session:
                # Query for available tasks
                query = session.query(TaskQueue, MediaLibrary).join(
                    MediaLibrary, TaskQueue.media_id == MediaLibrary.media_id
                ).filter(
                    and_(
                        TaskQueue.status.in_([
                            TaskStatus.PENDING,
                            TaskStatus.FAILED
                        ]),
                        TaskQueue.retry_count < config.MAX_FAILURE_COUNT,
                        MediaLibrary.existence_status == ExistenceStatus.EXISTS,
                    )
                ).order_by(TaskQueue.created_at.asc())

                result = query.first()

                if not result:
                    return None

                task, media = result

                # Update task with worker assignment
                now = datetime.now(timezone.utc)
                timeout_deadline = now + timedelta(seconds=config.TASK_TIMEOUT)

                task.worker_assignment = self.worker_id
                task.started_time = now
                task.timeout_deadline = timeout_deadline
                task.updated_at = now

                session.commit()

                # Return task info as dictionary
                return {
                    'task_id': task.task_id,
                    'media_id': media.media_id,
                    'media_title': media.title,
                    'media_type': media.media_type.value,
                    'nfo_file_path': task.nfo_file_path,
                    'video_file_path': task.video_file_path,
                    'directory_path': media.directory_path,
                    'status': task.status.value,
                    'retry_count': task.retry_count,
                }

        except Exception as e:
            logger.error(f"Error acquiring task: {e}", exc_info=True)
            return None

    async def process_task(self, task: Dict):
        """
        Process a task through metadata enrichment and media processing phases.

        Args:
            task: Task dictionary with all necessary information.
        """
        task_id = task['task_id']
        media_id = task['media_id']
        start_time = datetime.now(timezone.utc)

        try:
            # Pre-check: verify media files still exist on disk
            video_path = task['video_file_path']
            directory_path = task['directory_path']
            if not os.path.exists(video_path) or not os.path.exists(directory_path):
                logger.warning(
                    f"Task {task_id}: Media files no longer exist "
                    f"(video: {video_path}, directory: {directory_path}), marking as deleted"
                )
                await self._mark_media_deleted(media_id)
                await self._mark_task_failed(
                    task_id, media_id, start_time,
                    "media_not_found",
                    f"Video file or directory no longer exists: {video_path}"
                )
                return

            # Phase 1: Metadata Enrichment
            logger.info(f"Task {task_id}: Starting metadata enrichment phase")
            await self._update_task_status(task_id, TaskStatus.METADATA_FETCHING)

            metadata_success = await self.metadata_enricher.enrich_metadata(task)

            if not metadata_success:
                logger.error(f"Task {task_id}: Metadata enrichment failed")
                await self._mark_task_failed(
                    task_id,
                    media_id,
                    start_time,
                    "metadata_enrichment_failed",
                    "Failed to fetch or parse metadata"
                )
                return

            logger.info(f"Task {task_id}: Metadata enrichment completed")

            # Phase 2: Media Processing
            logger.info(f"Task {task_id}: Starting media processing phase")
            await self._update_task_status(task_id, TaskStatus.PROCESSING)

            subtitle_path = await self.media_processor.process_media(task)

            if not subtitle_path:
                logger.error(f"Task {task_id}: Media processing failed")
                await self._mark_task_failed(
                    task_id,
                    media_id,
                    start_time,
                    "media_processing_failed",
                    "Failed to generate subtitle"
                )
                return

            logger.info(f"Task {task_id}: Subtitle generated at {subtitle_path}")

            # Task completed successfully
            await self._mark_task_completed(task_id, media_id, start_time, subtitle_path)

        except Exception as e:
            logger.error(f"Task {task_id}: Unexpected error: {e}", exc_info=True)
            await self._mark_task_failed(
                task_id,
                media_id,
                start_time,
                "unexpected_error",
                str(e)
            )

    async def _update_task_status(self, task_id: int, status: TaskStatus):
        """Update task status in database."""
        try:
            with get_db_session() as session:
                task = session.query(TaskQueue).filter(TaskQueue.task_id == task_id).first()
                if task:
                    task.status = status
                    task.updated_at = datetime.now(timezone.utc)
                    session.commit()
        except Exception as e:
            logger.error(f"Error updating task status: {e}", exc_info=True)

    async def _mark_task_completed(
        self,
        task_id: int,
        media_id: int,
        start_time: datetime,
        subtitle_path: str
    ):
        """Mark task as completed and update media library."""
        try:
            with get_db_session() as session:
                end_time = datetime.now(timezone.utc)
                duration = int((end_time - start_time).total_seconds())

                # Update media library with subtitle path
                media = session.query(MediaLibrary).filter(
                    MediaLibrary.media_id == media_id
                ).first()

                if media:
                    media.subtitle_file_path = subtitle_path
                    media.updated_at = end_time

                # Remove task from queue
                task = session.query(TaskQueue).filter(TaskQueue.task_id == task_id).first()
                if task:
                    session.delete(task)

                # Add to processing history
                history = ProcessingHistory(
                    task_id=task_id,
                    media_id=media_id,
                    status=HistoryStatus.SUCCESS,
                    processing_duration_seconds=duration,
                    failure_reason=None,
                    error_details=None,
                    created_at=end_time,
                    updated_at=end_time,
                )
                session.add(history)

                session.commit()
                logger.info(f"Task {task_id}: Marked as completed")

        except Exception as e:
            logger.error(f"Error marking task as completed: {e}", exc_info=True)

    async def _mark_media_deleted(self, media_id: int):
        """Mark media as deleted in the library."""
        try:
            with get_db_session() as session:
                media = session.query(MediaLibrary).filter(
                    MediaLibrary.media_id == media_id
                ).first()
                if media:
                    media.existence_status = ExistenceStatus.DELETED
                    media.updated_at = datetime.now(timezone.utc)
                    session.commit()
                    logger.info(f"Media {media_id} marked as deleted")
        except Exception as e:
            logger.error(f"Error marking media {media_id} as deleted: {e}", exc_info=True)

    async def _mark_task_failed(
        self,
        task_id: int,
        media_id: int,
        start_time: datetime,
        failure_reason: str,
        error_details: str
    ):
        """Mark task as failed and increment retry count or move to history."""
        try:
            with get_db_session() as session:
                end_time = datetime.now(timezone.utc)
                duration = int((end_time - start_time).total_seconds())

                task = session.query(TaskQueue).filter(TaskQueue.task_id == task_id).first()

                if not task:
                    logger.error(f"Task {task_id} not found in queue")
                    return

                task.retry_count += 1
                task.updated_at = end_time

                # Check if we should remove from queue
                if task.retry_count >= config.MAX_FAILURE_COUNT:
                    logger.info(f"Task {task_id}: Max retries reached, moving to history")

                    # Add to processing history
                    history = ProcessingHistory(
                        task_id=task_id,
                        media_id=media_id,
                        status=HistoryStatus.FAILED,
                        processing_duration_seconds=duration,
                        failure_reason=failure_reason,
                        error_details=error_details,
                        created_at=end_time,
                        updated_at=end_time,
                    )
                    session.add(history)

                    # Remove from queue
                    session.delete(task)
                else:
                    # Keep in queue for retry
                    task.status = TaskStatus.FAILED
                    task.failure_reason = f"{failure_reason}: {error_details}"
                    task.worker_assignment = None
                    task.started_time = None
                    task.timeout_deadline = None

                session.commit()
                logger.info(f"Task {task_id}: Marked as failed (retry {task.retry_count}/{config.MAX_FAILURE_COUNT})")

        except Exception as e:
            logger.error(f"Error marking task as failed: {e}", exc_info=True)
