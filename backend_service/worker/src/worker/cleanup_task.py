"""Cleanup task for handling timeouts, failed tasks, and temporary files."""

import logging
import os
import shutil
from datetime import datetime, timezone, timedelta
from typing import Dict

import sys
sys.path.append('/app/shared')

from shared import (
    get_db_session,
    MediaLibrary,
    TaskQueue,
    ProcessingHistory,
    ExistenceStatus,
    TaskStatus,
    HistoryStatus,
    config,
)

logger = logging.getLogger(__name__)


class CleanupTask:
    """Handles cleanup operations for media library, tasks, and temporary files."""

    def __init__(self):
        self.temp_dir = config.TEMP_DIR
        self.temp_retention_hours = config.TEMP_RETENTION_HOURS
        self.task_timeout = config.TASK_TIMEOUT
        self.max_failure_count = config.MAX_FAILURE_COUNT

    async def run_cleanup(self) -> Dict[str, int]:
        """
        Run all cleanup operations.

        Returns:
            Dictionary with cleanup statistics.
        """
        logger.info("Starting cleanup task")

        stats = {
            'media_marked_deleted': 0,
            'tasks_timed_out': 0,
            'failed_tasks_archived': 0,
            'temp_dirs_cleaned': 0,
            'history_pruned': 0,
        }

        try:
            # 1. Media existence check
            media_count = await self._check_media_existence()
            stats['media_marked_deleted'] = media_count

            # 2. Timeout handling
            timeout_count = await self._handle_timeouts()
            stats['tasks_timed_out'] = timeout_count

            # 3. Failed task cleanup
            failed_count = await self._cleanup_failed_tasks()
            stats['failed_tasks_archived'] = failed_count

            # 4. Temporary directory cleanup
            temp_count = await self._cleanup_temp_directories()
            stats['temp_dirs_cleaned'] = temp_count

            # 5. History pruning (optional)
            # Commented out for now - can be enabled if needed
            # history_count = await self._prune_history()
            # stats['history_pruned'] = history_count

            logger.info(
                f"Cleanup completed: "
                f"{stats['media_marked_deleted']} media marked deleted, "
                f"{stats['tasks_timed_out']} tasks timed out, "
                f"{stats['failed_tasks_archived']} failed tasks archived, "
                f"{stats['temp_dirs_cleaned']} temp directories cleaned"
            )

            return stats

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            return stats

    async def _check_media_existence(self) -> int:
        """
        Check if media files still exist and mark as deleted if not.

        Returns:
            Number of media items marked as deleted.
        """
        count = 0

        try:
            with get_db_session() as session:
                # Query all media with status "exists"
                media_items = session.query(MediaLibrary).filter(
                    MediaLibrary.existence_status == ExistenceStatus.EXISTS
                ).all()

                for media in media_items:
                    # Check if directory still exists
                    if not os.path.exists(media.directory_path):
                        logger.info(
                            f"Media directory no longer exists: {media.directory_path} "
                            f"(media_id: {media.media_id}, title: {media.title})"
                        )

                        media.existence_status = ExistenceStatus.DELETED
                        media.updated_at = datetime.now(timezone.utc)
                        count += 1

                if count > 0:
                    session.commit()
                    logger.info(f"Marked {count} media items as deleted")

        except Exception as e:
            logger.error(f"Error checking media existence: {e}", exc_info=True)

        return count

    async def _handle_timeouts(self) -> int:
        """
        Handle timed-out tasks.

        Returns:
            Number of tasks moved to history due to timeout.
        """
        count = 0

        try:
            with get_db_session() as session:
                now = datetime.now(timezone.utc)

                # Query tasks with status "processing" that have timed out
                timed_out_tasks = session.query(TaskQueue).filter(
                    TaskQueue.status == TaskStatus.PROCESSING,
                    TaskQueue.timeout_deadline < now
                ).all()

                for task in timed_out_tasks:
                    logger.info(
                        f"Task {task.task_id} timed out "
                        f"(started: {task.started_time}, deadline: {task.timeout_deadline})"
                    )

                    # Calculate processing duration
                    if task.started_time:
                        duration = int((now - task.started_time).total_seconds())
                    else:
                        duration = 0

                    # Create history entry
                    history = ProcessingHistory(
                        task_id=task.task_id,
                        media_id=task.media_id,
                        status=HistoryStatus.FAILED,
                        processing_duration_seconds=duration,
                        failure_reason="timeout",
                        error_details=f"Task exceeded timeout of {self.task_timeout} seconds",
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(history)

                    # Remove from task queue
                    session.delete(task)
                    count += 1

                if count > 0:
                    session.commit()
                    logger.info(f"Moved {count} timed-out tasks to history")

        except Exception as e:
            logger.error(f"Error handling timeouts: {e}", exc_info=True)

        return count

    async def _cleanup_failed_tasks(self) -> int:
        """
        Move failed tasks with max retries to history.

        Returns:
            Number of failed tasks moved to history.
        """
        count = 0

        try:
            with get_db_session() as session:
                now = datetime.now(timezone.utc)

                # Query failed tasks that have reached max retry count
                failed_tasks = session.query(TaskQueue).filter(
                    TaskQueue.status == TaskStatus.FAILED,
                    TaskQueue.retry_count >= self.max_failure_count
                ).all()

                for task in failed_tasks:
                    logger.info(
                        f"Archiving failed task {task.task_id} "
                        f"(retry_count: {task.retry_count}/{self.max_failure_count})"
                    )

                    # Calculate processing duration
                    if task.started_time:
                        duration = int((now - task.started_time).total_seconds())
                    else:
                        duration = 0

                    # Create history entry
                    history = ProcessingHistory(
                        task_id=task.task_id,
                        media_id=task.media_id,
                        status=HistoryStatus.FAILED,
                        processing_duration_seconds=duration,
                        failure_reason=task.failure_reason or "unknown",
                        error_details=f"Failed after {task.retry_count} retries",
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(history)

                    # Remove from task queue
                    session.delete(task)
                    count += 1

                if count > 0:
                    session.commit()
                    logger.info(f"Archived {count} failed tasks to history")

        except Exception as e:
            logger.error(f"Error cleaning up failed tasks: {e}", exc_info=True)

        return count

    async def _cleanup_temp_directories(self) -> int:
        """
        Clean up temporary directories for completed/failed tasks.

        Returns:
            Number of directories cleaned.
        """
        count = 0

        try:
            if not os.path.exists(self.temp_dir):
                return 0

            now = datetime.now(timezone.utc)
            retention_threshold = now - timedelta(hours=self.temp_retention_hours)

            # List all directories in temp dir
            for item in os.listdir(self.temp_dir):
                item_path = os.path.join(self.temp_dir, item)

                # Skip if not a directory
                if not os.path.isdir(item_path):
                    continue

                # Check if it matches our pattern: {task_id}_{random}
                if '_' not in item:
                    continue

                try:
                    task_id_str = item.split('_')[0]
                    task_id = int(task_id_str)
                except (ValueError, IndexError):
                    # Not our pattern, skip
                    continue

                # Check if task still exists in queue
                with get_db_session() as session:
                    task_exists = session.query(TaskQueue).filter(
                        TaskQueue.task_id == task_id
                    ).first() is not None

                if task_exists:
                    # Task is still active, don't delete
                    continue

                # Task doesn't exist, check directory age
                dir_mtime = datetime.fromtimestamp(os.path.getmtime(item_path), tz=timezone.utc)

                if dir_mtime < retention_threshold:
                    # Directory is old enough, delete it
                    try:
                        shutil.rmtree(item_path)
                        logger.info(f"Cleaned up temp directory: {item_path}")
                        count += 1
                    except Exception as e:
                        logger.error(f"Error deleting temp directory {item_path}: {e}")

            if count > 0:
                logger.info(f"Cleaned up {count} temporary directories")

        except Exception as e:
            logger.error(f"Error cleaning up temp directories: {e}", exc_info=True)

        return count

    async def _prune_history(self, retention_days: int = 90) -> int:
        """
        Prune old processing history entries (optional).

        Args:
            retention_days: Number of days to retain history.

        Returns:
            Number of history entries deleted.
        """
        count = 0

        try:
            with get_db_session() as session:
                now = datetime.now(timezone.utc)
                cutoff_date = now - timedelta(days=retention_days)

                # Delete old history entries
                result = session.query(ProcessingHistory).filter(
                    ProcessingHistory.created_at < cutoff_date
                ).delete()

                count = result
                session.commit()

                if count > 0:
                    logger.info(f"Pruned {count} history entries older than {retention_days} days")

        except Exception as e:
            logger.error(f"Error pruning history: {e}", exc_info=True)

        return count
