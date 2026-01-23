"""Media scanner for discovering video files and NFO metadata."""

import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict

import sys
sys.path.append('/app/shared')

from shared import (
    get_db_session,
    MediaLibrary,
    TaskQueue,
    ProcessingHistory,
    MediaType,
    ExistenceStatus,
    TaskStatus,
    config,
)

logger = logging.getLogger(__name__)


class MediaScanner:
    """Scans media directory for NFO files and creates processing tasks."""

    def __init__(self):
        self.media_dir = config.MEDIA_DIR

    async def scan(self) -> Dict[str, int]:
        """
        Scan media directory for new NFO files.

        Returns:
            Dictionary with scan statistics.
        """
        logger.info(f"Starting media scan in: {self.media_dir}")

        stats = {
            'nfo_files_found': 0,
            'new_items_added': 0,
            'already_processed': 0,
            'errors': 0,
        }

        try:
            # Recursively find all NFO files
            nfo_files = self._find_nfo_files(self.media_dir)
            stats['nfo_files_found'] = len(nfo_files)

            logger.info(f"Found {len(nfo_files)} NFO files")

            # Process each NFO file
            for nfo_path in nfo_files:
                try:
                    result = await self._process_nfo_file(nfo_path)

                    if result == 'new':
                        stats['new_items_added'] += 1
                    elif result == 'existing':
                        stats['already_processed'] += 1

                except Exception as e:
                    logger.error(f"Error processing NFO file {nfo_path}: {e}", exc_info=True)
                    stats['errors'] += 1

            logger.info(
                f"Media scan completed: {stats['new_items_added']} new items added, "
                f"{stats['already_processed']} already processed, "
                f"{stats['errors']} errors"
            )

            return stats

        except Exception as e:
            logger.error(f"Error during media scan: {e}", exc_info=True)
            return stats

    def _find_nfo_files(self, directory: str) -> list:
        """
        Recursively find all NFO files in directory.

        Returns:
            List of absolute NFO file paths.
        """
        nfo_files = []

        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.nfo'):
                        full_path = os.path.join(root, file)
                        nfo_files.append(full_path)

        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}", exc_info=True)

        return nfo_files

    async def _process_nfo_file(self, nfo_path: str) -> str:
        """
        Process a single NFO file.

        Returns:
            'new' if new item was added, 'existing' if already processed.
        """
        # Check if already in database
        with get_db_session() as session:
            # Check in media library
            existing_media = session.query(MediaLibrary).filter(
                MediaLibrary.nfo_file_path == nfo_path
            ).first()

            if existing_media:
                return 'existing'

            # Check in task queue
            existing_task = session.query(TaskQueue).filter(
                TaskQueue.nfo_file_path == nfo_path
            ).first()

            if existing_task:
                return 'existing'

            # Check in processing history
            existing_history = session.query(ProcessingHistory).join(
                MediaLibrary, ProcessingHistory.media_id == MediaLibrary.media_id
            ).filter(
                MediaLibrary.nfo_file_path == nfo_path
            ).first()

            if existing_history:
                return 'existing'

        # Not found, parse NFO and create entries
        nfo_data = self._parse_nfo_basic(nfo_path)

        if not nfo_data:
            logger.error(f"Failed to parse NFO file: {nfo_path}")
            raise ValueError(f"Failed to parse NFO: {nfo_path}")

        # Find video file
        video_path = self._find_video_file(nfo_path, nfo_data.get('media_type'))

        if not video_path:
            logger.warning(f"No video file found for NFO: {nfo_path}")
            raise ValueError(f"No video file found for: {nfo_path}")

        # Find poster file
        poster_path = self._find_poster_file(nfo_path, nfo_data.get('media_type'), nfo_data.get('season'))

        # Create media library entry and task
        with get_db_session() as session:
            # Create media library entry
            media = MediaLibrary(
                tmdb_id=nfo_data.get('tmdb_id'),
                imdb_id=nfo_data.get('imdb_id'),
                media_type=nfo_data['media_type'],
                title=nfo_data.get('title', 'Unknown'),
                year=nfo_data.get('year'),
                overview=None,  # Will be enriched later
                cast=None,      # Will be enriched later
                season=nfo_data.get('season'),
                episode=nfo_data.get('episode'),
                episode_overview=None,  # Will be enriched later
                nfo_file_path=nfo_path,
                video_file_path=video_path,
                subtitle_file_path=None,
                poster_path=poster_path,
                directory_path=os.path.dirname(video_path),
                existence_status=ExistenceStatus.EXISTS,
            )

            session.add(media)
            session.flush()  # Get media_id

            # Create task
            task = TaskQueue(
                media_id=media.media_id,
                nfo_file_path=nfo_path,
                video_file_path=video_path,
                status=TaskStatus.PENDING,
                retry_count=0,
            )

            session.add(task)
            session.commit()

            logger.info(
                f"Created new media entry: {nfo_data.get('title')} "
                f"(media_id: {media.media_id}, task_id: {task.task_id})"
            )

        return 'new'

    def _parse_nfo_basic(self, nfo_path: str) -> Optional[Dict]:
        """
        Parse basic information from NFO file.

        Returns:
            Dictionary with basic metadata.
        """
        try:
            tree = ET.parse(nfo_path)
            root = tree.getroot()

            data = {}

            # Determine media type
            if root.find('season') is not None or root.find('episode') is not None:
                data['media_type'] = MediaType.TV
            else:
                data['media_type'] = MediaType.MOVIE

            # Extract basic fields
            data['title'] = self._get_text(root, 'title')
            data['year'] = self._get_int(root, 'year')
            data['tmdb_id'] = self._get_text(root, 'tmdbid') or self._get_text(root, 'id')
            data['imdb_id'] = self._get_text(root, 'imdbid')

            # TV show specific
            if data['media_type'] == MediaType.TV:
                data['season'] = self._get_int(root, 'season')
                data['episode'] = self._get_int(root, 'episode')

            return data

        except Exception as e:
            logger.error(f"Error parsing NFO file {nfo_path}: {e}", exc_info=True)
            return None

    def _get_text(self, root, tag: str) -> Optional[str]:
        """Get text from XML element."""
        elem = root.find(tag)
        return elem.text.strip() if elem is not None and elem.text else None

    def _get_int(self, root, tag: str) -> Optional[int]:
        """Get integer from XML element."""
        text = self._get_text(root, tag)
        try:
            return int(text) if text else None
        except (ValueError, TypeError):
            return None

    def _find_video_file(self, nfo_path: str, media_type: MediaType) -> Optional[str]:
        """
        Find video file corresponding to NFO file.

        Args:
            nfo_path: Path to NFO file.
            media_type: Type of media (movie or tv).

        Returns:
            Path to video file, or None if not found.
        """
        directory = os.path.dirname(nfo_path)
        nfo_basename = Path(nfo_path).stem

        # Common video extensions
        video_extensions = ['.mkv', '.mp4', '.avi', '.mov', '.m4v', '.ts']

        # For movies, NFO is typically movie.nfo
        # For TV shows, NFO is typically tvshow.nfo or same name as video
        if media_type == MediaType.MOVIE:
            # Look for any video file in the same directory
            for ext in video_extensions:
                # Try exact match first
                video_path = os.path.join(directory, f"{nfo_basename}{ext}")
                if os.path.exists(video_path):
                    return video_path

            # Try finding any video file in directory
            for file in os.listdir(directory):
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    return os.path.join(directory, file)

        else:  # TV show
            # Try exact match with NFO basename
            for ext in video_extensions:
                video_path = os.path.join(directory, f"{nfo_basename}{ext}")
                if os.path.exists(video_path):
                    return video_path

            # Try finding any video file in directory
            for file in os.listdir(directory):
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    return os.path.join(directory, file)

        return None

    def _find_poster_file(self, nfo_path: str, media_type: MediaType, season: Optional[int] = None) -> Optional[str]:
        """
        Find poster/artwork file for media.

        Follows Jellyfin/Emby naming conventions:
        - Movies: poster.jpg, movie.jpg, folder.jpg, or {movie_name}-poster.jpg
        - TV Shows: poster.jpg, folder.jpg, or season{XX}-poster.jpg for episodes

        Args:
            nfo_path: Path to NFO file.
            media_type: Type of media (movie or tv).
            season: Season number for TV shows.

        Returns:
            Path to poster file, or None if not found.
        """
        directory = os.path.dirname(nfo_path)
        nfo_basename = Path(nfo_path).stem

        # Common image extensions
        image_extensions = ['.jpg', '.jpeg', '.png']

        # Poster filename patterns to try (in priority order)
        poster_patterns = []

        if media_type == MediaType.MOVIE:
            # Movie poster patterns
            poster_patterns = [
                'poster',           # poster.jpg (most common)
                'movie',            # movie.jpg
                'folder',           # folder.jpg
                f'{nfo_basename}-poster',  # {movie_name}-poster.jpg
                nfo_basename,       # Same as video filename
            ]
        else:  # TV show episode
            if season is not None:
                # TV episode poster patterns
                poster_patterns = [
                    f'season{season:02d}-poster',  # season01-poster.jpg
                    f'season{season}-poster',      # season1-poster.jpg
                    'poster',                      # poster.jpg (show poster)
                    'folder',                      # folder.jpg
                ]
            else:
                # Fallback if no season info
                poster_patterns = ['poster', 'folder']

        # Try to find poster with each pattern and extension
        for pattern in poster_patterns:
            for ext in image_extensions:
                poster_path = os.path.join(directory, f"{pattern}{ext}")
                if os.path.exists(poster_path):
                    logger.debug(f"Found poster: {poster_path}")
                    return poster_path

        # If no specific poster found, check parent directory for TV show poster
        if media_type == MediaType.TV:
            parent_dir = os.path.dirname(directory)
            for pattern in ['poster', 'folder']:
                for ext in image_extensions:
                    poster_path = os.path.join(parent_dir, f"{pattern}{ext}")
                    if os.path.exists(poster_path):
                        logger.debug(f"Found show poster in parent directory: {poster_path}")
                        return poster_path

        logger.debug(f"No poster found for: {nfo_path}")
        return None
