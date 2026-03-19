"""Main worker service entry point."""

import asyncio
import logging
import sys
from datetime import datetime, timezone

sys.path.append('/app/shared')

from shared import config, init_db, get_db_session, TaskQueue, TaskStatus
from .task_processor import TaskProcessor
from .media_scanner import MediaScanner
from .cleanup_task import CleanupTask

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


class WorkerService:
    """Main worker service coordinating task processing and scheduled tasks."""

    def __init__(self):
        self.worker_id = config.WORKER_ID
        self.max_concurrent_workers = config.MAX_CONCURRENT_WORKERS
        self.poll_interval = config.WORKER_POLL_INTERVAL
        self.scan_interval = config.SCAN_INTERVAL
        self.cleanup_interval = config.CLEANUP_INTERVAL

        self.active_tasks = set()
        self.task_processor = TaskProcessor(self.worker_id)
        self.media_scanner = MediaScanner()
        self.cleanup_task = CleanupTask()
        self.running = False

    async def start(self):
        """Start the worker service with all scheduled tasks."""
        logger.info(f"Starting worker service: {self.worker_id}")
        logger.info(f"Max concurrent workers: {self.max_concurrent_workers}")
        logger.info(f"Poll interval: {self.poll_interval}s")
        logger.info(f"Media scan interval: {self.scan_interval}s")
        logger.info(f"Cleanup interval: {self.cleanup_interval}s")

        # Initialize database
        init_db()
        logger.info("Database initialized")

        # Reset tasks interrupted by previous restart
        self._reset_interrupted_tasks()

        self.running = True

        try:
            # Launch all background tasks
            await asyncio.gather(
                self._task_processing_loop(),
                self._media_scanner_loop(),
                self._cleanup_loop(),
            )
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.running = False
        except Exception as e:
            logger.error(f"Fatal error in worker service: {e}", exc_info=True)
            raise

    def _reset_interrupted_tasks(self):
        """Reset tasks that were interrupted by a previous restart back to PENDING."""
        try:
            with get_db_session() as session:
                interrupted = session.query(TaskQueue).filter(
                    TaskQueue.status.in_([TaskStatus.PROCESSING, TaskStatus.METADATA_FETCHING])
                ).all()

                if not interrupted:
                    return

                for task in interrupted:
                    task.status = TaskStatus.PENDING
                    task.worker_assignment = None
                    task.started_time = None
                    task.timeout_deadline = None

                session.commit()
                logger.info(f"Reset {len(interrupted)} interrupted task(s) to PENDING")

        except Exception as e:
            logger.error(f"Error resetting interrupted tasks: {e}", exc_info=True)

    async def _task_processing_loop(self):
        """Main task processing loop."""
        logger.info("Starting task processing loop")

        while self.running:
            try:
                # Check if we can spawn more workers
                current_active = len(self.active_tasks)

                if current_active < self.max_concurrent_workers:
                    # Try to acquire a task
                    task = await self.task_processor.acquire_next_task()

                    if task:
                        logger.info(f"Acquired task {task['task_id']} for media: {task['media_title']}")

                        # Spawn async task to process it
                        task_coroutine = self._process_task_wrapper(task)
                        asyncio.create_task(task_coroutine)
                    else:
                        logger.debug(f"No tasks available. Active: {current_active}/{self.max_concurrent_workers}")
                else:
                    logger.debug(f"Max concurrent workers reached: {current_active}/{self.max_concurrent_workers}")

                # Sleep until next poll
                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Error in task processing loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _media_scanner_loop(self):
        """Media scanner scheduled task loop."""
        logger.info("Starting media scanner loop")

        # Run initial scan immediately
        try:
            logger.info("Running initial media scan")
            stats = await self.media_scanner.scan()
            logger.info(f"Initial scan completed: {stats}")
        except Exception as e:
            logger.error(f"Error in initial media scan: {e}", exc_info=True)

        # Run periodic scans
        while self.running:
            try:
                await asyncio.sleep(self.scan_interval)

                if not self.running:
                    break

                logger.info("Running scheduled media scan")
                stats = await self.media_scanner.scan()
                logger.info(f"Scheduled scan completed: {stats}")

            except Exception as e:
                logger.error(f"Error in media scanner loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait a bit before retrying

    async def _cleanup_loop(self):
        """Cleanup scheduled task loop."""
        logger.info("Starting cleanup loop")

        # Run initial cleanup after a short delay
        await asyncio.sleep(60)  # Wait 1 minute before first cleanup

        try:
            logger.info("Running initial cleanup")
            stats = await self.cleanup_task.run_cleanup()
            logger.info(f"Initial cleanup completed: {stats}")
        except Exception as e:
            logger.error(f"Error in initial cleanup: {e}", exc_info=True)

        # Run periodic cleanups
        while self.running:
            try:
                await asyncio.sleep(self.cleanup_interval)

                if not self.running:
                    break

                logger.info("Running scheduled cleanup")
                stats = await self.cleanup_task.run_cleanup()
                logger.info(f"Scheduled cleanup completed: {stats}")

            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait a bit before retrying

    async def _process_task_wrapper(self, task: dict):
        """Wrapper to track active tasks and handle completion."""
        task_id = task['task_id']
        self.active_tasks.add(task_id)

        try:
            logger.info(f"Starting processing task {task_id}")
            await self.task_processor.process_task(task)
            logger.info(f"Completed processing task {task_id}")
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
        finally:
            self.active_tasks.discard(task_id)
            logger.debug(f"Task {task_id} removed from active set. Active: {len(self.active_tasks)}")


async def main():
    """Main entry point."""
    worker = WorkerService()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
