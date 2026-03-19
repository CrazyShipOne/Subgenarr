"""Metadata enrichment module for fetching and parsing media metadata."""

import logging
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List
import httpx
import json

import sys
sys.path.append('/app/shared')

from shared import (
    get_db_session,
    MediaLibrary,
    config,
)

logger = logging.getLogger(__name__)


class MetadataEnricher:
    """Handles metadata parsing and enrichment from NFO files and external APIs."""

    def __init__(self):
        self.tmdb_api_key = config.TMDB_API_KEY
        self.omdb_api_key = config.OMDB_API_KEY
        self.timeout = config.METADATA_API_TIMEOUT
        self.http_proxy = config.HTTP_PROXY

    async def enrich_metadata(self, task: Dict) -> bool:
        """
        Enrich metadata for a media item.

        Args:
            task: Task dictionary containing NFO path and media info.

        Returns:
            True if successful, False otherwise.
        """
        try:
            media_id = task['media_id']
            nfo_path = task['nfo_file_path']

            # Parse NFO file
            logger.info(f"Parsing NFO file: {nfo_path}")
            nfo_data = self._parse_nfo(nfo_path)

            if not nfo_data:
                logger.error(f"Failed to parse NFO file: {nfo_path}")
                return False

            # Check if metadata is complete
            is_complete = self._is_metadata_complete(nfo_data, task['media_type'])

            # If incomplete, fetch from external APIs
            if not is_complete:
                logger.info(f"Metadata incomplete, fetching from external APIs")

                tmdb_id = nfo_data.get('tmdb_id')
                imdb_id = nfo_data.get('imdb_id')
                title = nfo_data.get('title')
                year = nfo_data.get('year')

                if task['media_type'] == 'movie':
                    external_data = await self._fetch_movie_metadata(tmdb_id, imdb_id, title, year)
                else:
                    season = nfo_data.get('season')
                    episode = nfo_data.get('episode')
                    external_data = await self._fetch_tv_metadata(tmdb_id, imdb_id, title, year, season, episode)

                if external_data:
                    # Merge external data with NFO data
                    nfo_data.update(external_data)
                    logger.info(f"External metadata fetched successfully")
                else:
                    logger.warning(f"Failed to fetch external metadata, using NFO data only")

            # Update database
            await self._update_media_library(media_id, nfo_data)
            logger.info(f"Media library updated for media_id: {media_id}")

            return True

        except Exception as e:
            logger.error(f"Error enriching metadata: {e}", exc_info=True)
            return False

    def _parse_nfo(self, nfo_path: str) -> Optional[Dict]:
        """
        Parse NFO file (Jellyfin/Emby XML format).

        Returns:
            Dictionary with parsed metadata or None if failed.
        """
        try:
            tree = ET.parse(nfo_path)
            root = tree.getroot()

            data = {}

            # Common fields
            data['year'] = self._get_int(root, 'year')
            data['overview'] = self._get_text(root, 'plot')
            data['tmdb_id'] = self._get_text(root, 'tmdbid') or self._get_text(root, 'id')
            data['imdb_id'] = self._get_text(root, 'imdbid')

            # Cast
            actors = []
            for actor in root.findall('.//actor/name'):
                if actor.text:
                    actors.append(actor.text)
            data['cast'] = json.dumps(actors) if actors else None

            # TV show specific fields
            if root.find('season') is not None:
                data['season'] = self._get_int(root, 'season')
                data['episode'] = self._get_int(root, 'episode')
                data['episode_overview'] = self._get_text(root, 'plot')
                # Use <showtitle> for the series name; fall back to <title>
                data['title'] = (
                    self._get_text(root, 'showtitle') or
                    self._get_text(root, 'title')
                )
            else:
                data['title'] = self._get_text(root, 'title')

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

    def _is_metadata_complete(self, data: Dict, media_type: str) -> bool:
        """
        Check if metadata is complete.

        Required fields:
        - All: title, year, overview
        - TV: season, episode, episode_overview
        """
        required = ['title', 'overview']

        if media_type == 'tv':
            required.extend(['season', 'episode', 'episode_overview'])

        for field in required:
            if not data.get(field):
                logger.debug(f"Missing required field: {field}")
                return False

        return True

    async def _fetch_movie_metadata(
        self,
        tmdb_id: Optional[str],
        imdb_id: Optional[str],
        title: Optional[str],
        year: Optional[int]
    ) -> Optional[Dict]:
        """Fetch movie metadata from TMDb or OMDb."""
        # Try TMDb first
        if self.tmdb_api_key:
            data = await self._fetch_from_tmdb_movie(tmdb_id, title, year)
            if data:
                return data

        # Fallback to OMDb
        if self.omdb_api_key and (imdb_id or title):
            data = await self._fetch_from_omdb(imdb_id, title, year)
            if data:
                return data

        return None

    async def _fetch_tv_metadata(
        self,
        tmdb_id: Optional[str],
        imdb_id: Optional[str],
        title: Optional[str],
        year: Optional[int],
        season: Optional[int],
        episode: Optional[int]
    ) -> Optional[Dict]:
        """Fetch TV show metadata from TMDb or OMDb."""
        # Try TMDb first
        if self.tmdb_api_key:
            data = await self._fetch_from_tmdb_tv(tmdb_id, title, year, season, episode)
            if data:
                return data

        # Fallback to OMDb
        if self.omdb_api_key and (imdb_id or title):
            data = await self._fetch_from_omdb(imdb_id, title, year, season, episode)
            if data:
                return data

        return None

    async def _fetch_from_tmdb_movie(
        self,
        tmdb_id: Optional[str],
        title: Optional[str],
        year: Optional[int]
    ) -> Optional[Dict]:
        """Fetch movie metadata from TMDb API."""
        try:
            proxies = {"http://": self.http_proxy, "https://": self.http_proxy} if self.http_proxy else None

            async with httpx.AsyncClient(proxies=proxies, timeout=self.timeout) as client:
                # If we have TMDB ID, use it directly
                if tmdb_id:
                    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
                    params = {"api_key": self.tmdb_api_key}
                    response = await client.get(url, params=params)

                    if response.status_code == 200:
                        data = response.json()
                        return self._parse_tmdb_movie(data)

                # Otherwise search by title
                if title:
                    url = "https://api.themoviedb.org/3/search/movie"
                    params = {
                        "api_key": self.tmdb_api_key,
                        "query": title,
                    }
                    if year:
                        params["year"] = year

                    response = await client.get(url, params=params)

                    if response.status_code == 200:
                        results = response.json().get('results', [])
                        if results:
                            # Get full details for first result
                            movie_id = results[0]['id']
                            url = f"https://api.themoviedb.org/3/movie/{movie_id}"
                            params = {"api_key": self.tmdb_api_key}
                            response = await client.get(url, params=params)

                            if response.status_code == 200:
                                return self._parse_tmdb_movie(response.json())

        except Exception as e:
            logger.error(f"Error fetching from TMDb: {e}", exc_info=True)

        return None

    async def _fetch_from_tmdb_tv(
        self,
        tmdb_id: Optional[str],
        title: Optional[str],
        year: Optional[int],
        season: Optional[int],
        episode: Optional[int]
    ) -> Optional[Dict]:
        """Fetch TV show metadata from TMDb API."""
        try:
            proxies = {"http://": self.http_proxy, "https://": self.http_proxy} if self.http_proxy else None

            async with httpx.AsyncClient(proxies=proxies, timeout=self.timeout) as client:
                show_id = tmdb_id

                # If we don't have TMDB ID, search for it
                if not show_id and title:
                    url = "https://api.themoviedb.org/3/search/tv"
                    params = {
                        "api_key": self.tmdb_api_key,
                        "query": title,
                    }
                    if year:
                        params["first_air_date_year"] = year

                    response = await client.get(url, params=params)

                    if response.status_code == 200:
                        results = response.json().get('results', [])
                        if results:
                            show_id = str(results[0]['id'])

                # Fetch show details
                if show_id and season is not None and episode is not None:
                    # Get episode details
                    url = f"https://api.themoviedb.org/3/tv/{show_id}/season/{season}/episode/{episode}"
                    params = {"api_key": self.tmdb_api_key}
                    response = await client.get(url, params=params)

                    if response.status_code == 200:
                        episode_data = response.json()

                        # Also get show details for cast
                        url = f"https://api.themoviedb.org/3/tv/{show_id}"
                        params = {"api_key": self.tmdb_api_key}
                        show_response = await client.get(url, params=params)

                        if show_response.status_code == 200:
                            show_data = show_response.json()
                            return self._parse_tmdb_tv(show_data, episode_data)

        except Exception as e:
            logger.error(f"Error fetching from TMDb: {e}", exc_info=True)

        return None

    def _parse_tmdb_movie(self, data: Dict) -> Dict:
        """Parse TMDb movie response."""
        result = {}

        if data.get('title'):
            result['title'] = data['title']
        if data.get('release_date'):
            try:
                result['year'] = int(data['release_date'][:4])
            except (ValueError, TypeError):
                pass
        if data.get('overview'):
            result['overview'] = data['overview']
        if data.get('id'):
            result['tmdb_id'] = str(data['id'])

        return result

    def _parse_tmdb_tv(self, show_data: Dict, episode_data: Dict) -> Dict:
        """Parse TMDb TV show response."""
        result = {}

        if show_data.get('name'):
            result['title'] = show_data['name']
        if show_data.get('first_air_date'):
            try:
                result['year'] = int(show_data['first_air_date'][:4])
            except (ValueError, TypeError):
                pass
        if show_data.get('overview'):
            result['overview'] = show_data['overview']
        if show_data.get('id'):
            result['tmdb_id'] = str(show_data['id'])

        if episode_data.get('overview'):
            result['episode_overview'] = episode_data['overview']
        if episode_data.get('season_number') is not None:
            result['season'] = episode_data['season_number']
        if episode_data.get('episode_number') is not None:
            result['episode'] = episode_data['episode_number']

        return result

    async def _fetch_from_omdb(
        self,
        imdb_id: Optional[str],
        title: Optional[str],
        year: Optional[int],
        season: Optional[int] = None,
        episode: Optional[int] = None
    ) -> Optional[Dict]:
        """Fetch metadata from OMDb API."""
        try:
            proxies = {"http://": self.http_proxy, "https://": self.http_proxy} if self.http_proxy else None

            async with httpx.AsyncClient(proxies=proxies, timeout=self.timeout) as client:
                url = "http://www.omdbapi.com/"
                params = {"apikey": self.omdb_api_key}

                if imdb_id:
                    params["i"] = imdb_id
                elif title:
                    params["t"] = title
                    if year:
                        params["y"] = year

                if season is not None:
                    params["Season"] = season
                if episode is not None:
                    params["Episode"] = episode

                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if data.get('Response') == 'True':
                        return self._parse_omdb(data)

        except Exception as e:
            logger.error(f"Error fetching from OMDb: {e}", exc_info=True)

        return None

    def _parse_omdb(self, data: Dict) -> Dict:
        """Parse OMDb response."""
        result = {}

        if data.get('Title'):
            result['title'] = data['Title']
        if data.get('Year'):
            try:
                # OMDb year might be like "2008-2013" for TV shows
                year_str = data['Year'].split('-')[0]
                result['year'] = int(year_str)
            except (ValueError, TypeError):
                pass
        if data.get('Plot'):
            result['overview'] = data['Plot']
            result['episode_overview'] = data['Plot']  # For TV episodes
        if data.get('imdbID'):
            result['imdb_id'] = data['imdbID']

        return result

    async def _update_media_library(self, media_id: int, metadata: Dict):
        """Update media library with enriched metadata."""
        try:
            with get_db_session() as session:
                media = session.query(MediaLibrary).filter(
                    MediaLibrary.media_id == media_id
                ).first()

                if not media:
                    logger.error(f"Media {media_id} not found in database")
                    return

                # Update fields if present in metadata
                if metadata.get('title'):
                    media.title = metadata['title']
                if metadata.get('year'):
                    media.year = metadata['year']
                if metadata.get('overview'):
                    media.overview = metadata['overview']
                if metadata.get('tmdb_id'):
                    media.tmdb_id = metadata['tmdb_id']
                if metadata.get('imdb_id'):
                    media.imdb_id = metadata['imdb_id']
                if metadata.get('cast'):
                    media.cast = metadata['cast']
                if metadata.get('season') is not None:
                    media.season = metadata['season']
                if metadata.get('episode') is not None:
                    media.episode = metadata['episode']
                if metadata.get('episode_overview'):
                    media.episode_overview = metadata['episode_overview']

                session.commit()
                logger.info(f"Updated media library for media_id {media_id}")

        except Exception as e:
            logger.error(f"Error updating media library: {e}", exc_info=True)
            raise
