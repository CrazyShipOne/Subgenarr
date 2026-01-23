"""Media catalog API routes."""

import os
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, Response
from typing import Optional, List
from sqlalchemy import and_, or_, func

import sys
sys.path.append('/app/shared')

from shared import (
    get_db_session,
    MediaLibrary,
    TaskQueue,
    MediaType,
    ExistenceStatus,
    TaskStatus,
)
from api.middleware.auth import get_current_user
from api.schemas import MediaListResponse, MediaDetailResponse, MediaFilesResponse

router = APIRouter(prefix="/media", tags=["Media Catalog"])


def get_processing_status(media: MediaLibrary, session) -> str:
    """Determine processing status for a media item."""
    # Check if has subtitle
    if media.subtitle_file_path:
        return "completed"

    # Check if has active task
    task = session.query(TaskQueue).filter(
        TaskQueue.media_id == media.media_id
    ).first()

    if task:
        if task.status == TaskStatus.PROCESSING:
            return "processing"
        elif task.status == TaskStatus.PENDING:
            return "pending"
        elif task.status == TaskStatus.METADATA_FETCHING:
            return "processing"
        elif task.status == TaskStatus.FAILED:
            return "failed"

    return "unprocessed"


def parse_cast(cast_json: Optional[str]) -> Optional[List[str]]:
    """Parse cast JSON string to list."""
    if not cast_json:
        return None
    try:
        return json.loads(cast_json)
    except:
        return None


@router.get("/movies", response_model=MediaListResponse)
async def list_movies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    year: Optional[int] = None,
    has_subtitle: Optional[bool] = None,
    user: dict = Depends(get_current_user)
):
    """List all movies in the media library."""
    try:
        with get_db_session() as session:
            # Base query
            query = session.query(MediaLibrary).filter(
                and_(
                    MediaLibrary.media_type == MediaType.MOVIE,
                    MediaLibrary.existence_status == ExistenceStatus.EXISTS
                )
            )

            # Apply filters
            if search:
                query = query.filter(MediaLibrary.title.ilike(f"%{search}%"))

            if year:
                query = query.filter(MediaLibrary.year == year)

            if has_subtitle is not None:
                if has_subtitle:
                    query = query.filter(MediaLibrary.subtitle_file_path.isnot(None))
                else:
                    query = query.filter(MediaLibrary.subtitle_file_path.is_(None))

            # Get total count
            total_items = query.count()

            # Apply pagination
            offset = (page - 1) * page_size
            items = query.order_by(MediaLibrary.title.asc()).offset(offset).limit(page_size).all()

            # Format response
            media_items = []
            for media in items:
                media_items.append({
                    "media_id": media.media_id,
                    "media_type": "movie",
                    "title": media.title,
                    "year": media.year,
                    "overview": media.overview,
                    "tmdb_id": media.tmdb_id,
                    "imdb_id": media.imdb_id,
                    "cast": parse_cast(media.cast),
                    "video_file_path": media.video_file_path,
                    "subtitle_file_path": media.subtitle_file_path,
                    "has_poster": bool(media.poster_path and os.path.exists(media.poster_path)),
                    "directory_path": media.directory_path,
                    "existence_status": media.existence_status.value,
                    "processing_status": get_processing_status(media, session),
                    "created_at": media.created_at.isoformat(),
                    "updated_at": media.updated_at.isoformat(),
                })

            total_pages = (total_items + page_size - 1) // page_size

            return MediaListResponse(
                success=True,
                data={
                    "items": media_items,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_items": total_items,
                        "total_pages": total_pages,
                    }
                }
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tvshows/grouped", response_model=MediaListResponse)
async def list_tvshows_grouped(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    year: Optional[int] = None,
    user: dict = Depends(get_current_user)
):
    """List TV shows grouped by show title (one entry per show)."""
    try:
        with get_db_session() as session:
            # Subquery to get one representative episode per show
            subquery = session.query(
                MediaLibrary.title,
                func.min(MediaLibrary.media_id).label('first_media_id')
            ).filter(
                and_(
                    MediaLibrary.media_type == MediaType.TV,
                    MediaLibrary.existence_status == ExistenceStatus.EXISTS
                )
            ).group_by(MediaLibrary.title)

            # Apply search filter to subquery
            if search:
                subquery = subquery.filter(MediaLibrary.title.ilike(f"%{search}%"))

            if year:
                subquery = subquery.filter(MediaLibrary.year == year)

            subquery = subquery.subquery()

            # Get total count of unique shows
            total_items = session.query(func.count()).select_from(subquery).scalar()

            # Get paginated shows with aggregated data
            offset = (page - 1) * page_size

            shows_query = session.query(
                MediaLibrary.title,
                func.min(MediaLibrary.media_id).label('media_id'),
                func.min(MediaLibrary.year).label('year'),
                func.min(MediaLibrary.overview).label('overview'),
                func.min(MediaLibrary.tmdb_id).label('tmdb_id'),
                func.min(MediaLibrary.imdb_id).label('imdb_id'),
                func.min(MediaLibrary.cast).label('cast'),
                func.count(func.distinct(MediaLibrary.season)).label('season_count'),
                func.count(MediaLibrary.media_id).label('episode_count'),
                func.min(MediaLibrary.poster_path).label('poster_path'),
                func.min(MediaLibrary.created_at).label('created_at'),
                func.max(MediaLibrary.updated_at).label('updated_at'),
            ).filter(
                and_(
                    MediaLibrary.media_type == MediaType.TV,
                    MediaLibrary.existence_status == ExistenceStatus.EXISTS
                )
            )

            # Apply filters
            if search:
                shows_query = shows_query.filter(MediaLibrary.title.ilike(f"%{search}%"))

            if year:
                shows_query = shows_query.filter(MediaLibrary.year == year)

            shows_query = shows_query.group_by(MediaLibrary.title).order_by(MediaLibrary.title.asc())

            # Apply pagination
            shows = shows_query.offset(offset).limit(page_size).all()

            # Format response
            show_items = []
            for show in shows:
                # Check if poster exists
                has_poster = bool(show.poster_path and os.path.exists(show.poster_path))

                show_items.append({
                    "media_id": show.media_id,  # First episode's ID for detail page link
                    "media_type": "tv",
                    "title": show.title,
                    "year": show.year,
                    "overview": show.overview,
                    "tmdb_id": show.tmdb_id,
                    "imdb_id": show.imdb_id,
                    "cast": parse_cast(show.cast),
                    "season_count": show.season_count,
                    "episode_count": show.episode_count,
                    "has_poster": has_poster,
                    "created_at": show.created_at.isoformat() if show.created_at else None,
                    "updated_at": show.updated_at.isoformat() if show.updated_at else None,
                })

            total_pages = (total_items + page_size - 1) // page_size

            return MediaListResponse(
                success=True,
                data={
                    "items": show_items,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_items": total_items,
                        "total_pages": total_pages,
                    }
                }
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tvshows", response_model=MediaListResponse)
async def list_tvshows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    year: Optional[int] = None,
    season: Optional[int] = None,
    user: dict = Depends(get_current_user)
):
    """List all TV shows in the media library."""
    try:
        with get_db_session() as session:
            # Base query
            query = session.query(MediaLibrary).filter(
                and_(
                    MediaLibrary.media_type == MediaType.TV,
                    MediaLibrary.existence_status == ExistenceStatus.EXISTS
                )
            )

            # Apply filters
            if search:
                query = query.filter(MediaLibrary.title.ilike(f"%{search}%"))

            if year:
                query = query.filter(MediaLibrary.year == year)

            if season:
                query = query.filter(MediaLibrary.season == season)

            # Get total count
            total_items = query.count()

            # Apply pagination
            offset = (page - 1) * page_size
            items = query.order_by(
                MediaLibrary.title.asc(),
                MediaLibrary.season.asc(),
                MediaLibrary.episode.asc()
            ).offset(offset).limit(page_size).all()

            # Format response
            media_items = []
            for media in items:
                media_items.append({
                    "media_id": media.media_id,
                    "media_type": "tv",
                    "title": media.title,
                    "year": media.year,
                    "overview": media.overview,
                    "tmdb_id": media.tmdb_id,
                    "imdb_id": media.imdb_id,
                    "cast": parse_cast(media.cast),
                    "season": media.season,
                    "episode": media.episode,
                    "episode_overview": media.episode_overview,
                    "video_file_path": media.video_file_path,
                    "subtitle_file_path": media.subtitle_file_path,
                    "has_poster": bool(media.poster_path and os.path.exists(media.poster_path)),
                    "directory_path": media.directory_path,
                    "existence_status": media.existence_status.value,
                    "processing_status": get_processing_status(media, session),
                    "created_at": media.created_at.isoformat(),
                    "updated_at": media.updated_at.isoformat(),
                })

            total_pages = (total_items + page_size - 1) // page_size

            return MediaListResponse(
                success=True,
                data={
                    "items": media_items,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_items": total_items,
                        "total_pages": total_pages,
                    }
                }
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tvshows/detail/{show_title:path}")
async def get_tvshow_detail(
    show_title: str,
    user: dict = Depends(get_current_user)
):
    """Get detailed hierarchical information for a TV show (seasons → episodes)."""
    try:
        with get_db_session() as session:
            # Get all episodes for this show
            episodes = session.query(MediaLibrary).filter(
                and_(
                    MediaLibrary.media_type == MediaType.TV,
                    MediaLibrary.title == show_title,
                    MediaLibrary.existence_status == ExistenceStatus.EXISTS
                )
            ).order_by(
                MediaLibrary.season.asc(),
                MediaLibrary.episode.asc()
            ).all()

            if not episodes:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="TV show not found"
                )

            # Get show-level metadata from first episode
            first_episode = episodes[0]

            # Group episodes by season
            seasons_dict = {}
            for ep in episodes:
                season_num = ep.season if ep.season is not None else 0

                if season_num not in seasons_dict:
                    seasons_dict[season_num] = {
                        "season_number": season_num,
                        "episodes": []
                    }

                # Check processing status for this episode
                processing_status = get_processing_status(ep, session)

                seasons_dict[season_num]["episodes"].append({
                    "media_id": ep.media_id,
                    "episode_number": ep.episode,
                    "episode_overview": ep.episode_overview,
                    "video_file_path": ep.video_file_path,
                    "subtitle_file_path": ep.subtitle_file_path,
                    "has_poster": bool(ep.poster_path and os.path.exists(ep.poster_path)),
                    "processing_status": processing_status,
                    "created_at": ep.created_at.isoformat(),
                    "updated_at": ep.updated_at.isoformat(),
                })

            # Convert seasons dict to sorted list
            seasons = [seasons_dict[key] for key in sorted(seasons_dict.keys())]

            # Build response
            data = {
                "title": first_episode.title,
                "media_type": "tv",
                "year": first_episode.year,
                "overview": first_episode.overview,
                "tmdb_id": first_episode.tmdb_id,
                "imdb_id": first_episode.imdb_id,
                "cast": parse_cast(first_episode.cast),
                "has_poster": bool(first_episode.poster_path and os.path.exists(first_episode.poster_path)),
                "season_count": len(seasons),
                "episode_count": len(episodes),
                "seasons": seasons,
            }

            return {
                "success": True,
                "data": data
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{media_id}", response_model=MediaDetailResponse)
async def get_media_detail(
    media_id: int,
    user: dict = Depends(get_current_user)
):
    """Get detailed information for a specific media item."""
    try:
        with get_db_session() as session:
            media = session.query(MediaLibrary).filter(
                MediaLibrary.media_id == media_id
            ).first()

            if not media:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Media not found"
                )

            data = {
                "media_id": media.media_id,
                "media_type": media.media_type.value,
                "title": media.title,
                "year": media.year,
                "overview": media.overview,
                "tmdb_id": media.tmdb_id,
                "imdb_id": media.imdb_id,
                "cast": parse_cast(media.cast),
                "season": media.season,
                "episode": media.episode,
                "episode_overview": media.episode_overview,
                "video_file_path": media.video_file_path,
                "nfo_file_path": media.nfo_file_path,
                "subtitle_file_path": media.subtitle_file_path,
                "has_poster": bool(media.poster_path and os.path.exists(media.poster_path)),
                "directory_path": media.directory_path,
                "existence_status": media.existence_status.value,
                "processing_status": get_processing_status(media, session),
                "created_at": media.created_at.isoformat(),
                "updated_at": media.updated_at.isoformat(),
            }

            return MediaDetailResponse(success=True, data=data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{media_id}/files", response_model=MediaFilesResponse)
async def get_media_files(
    media_id: int,
    user: dict = Depends(get_current_user)
):
    """List all files associated with a media item."""
    try:
        with get_db_session() as session:
            media = session.query(MediaLibrary).filter(
                MediaLibrary.media_id == media_id
            ).first()

            if not media:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Media not found"
                )

            # Prepare file info
            files = {}

            # Video file
            if media.video_file_path:
                video_exists = os.path.exists(media.video_file_path)
                files["video"] = {
                    "path": media.video_file_path,
                    "size_bytes": os.path.getsize(media.video_file_path) if video_exists else 0,
                    "exists": video_exists,
                }

            # NFO file
            if media.nfo_file_path:
                nfo_exists = os.path.exists(media.nfo_file_path)
                files["nfo"] = {
                    "path": media.nfo_file_path,
                    "size_bytes": os.path.getsize(media.nfo_file_path) if nfo_exists else 0,
                    "exists": nfo_exists,
                }

            # Generated subtitle
            if media.subtitle_file_path:
                subtitle_exists = os.path.exists(media.subtitle_file_path)
                # Extract language from filename (e.g., filename_en_0.srt)
                language = None
                if subtitle_exists:
                    basename = os.path.basename(media.subtitle_file_path)
                    parts = basename.rsplit('_', 2)
                    if len(parts) >= 2:
                        language = parts[-2]

                files["generated_subtitle"] = {
                    "path": media.subtitle_file_path,
                    "size_bytes": os.path.getsize(media.subtitle_file_path) if subtitle_exists else 0,
                    "language": language,
                    "exists": subtitle_exists,
                }

            # Other subtitles in directory
            other_subtitles = []
            if os.path.exists(media.directory_path):
                for file in os.listdir(media.directory_path):
                    if file.endswith('.srt') and os.path.join(media.directory_path, file) != media.subtitle_file_path:
                        file_path = os.path.join(media.directory_path, file)
                        # Try to detect language
                        language = None
                        if '.zh.' in file or '_zh.' in file:
                            language = 'zh'
                        elif '.en.' in file or '_en.' in file:
                            language = 'en'

                        other_subtitles.append({
                            "path": file_path,
                            "size_bytes": os.path.getsize(file_path),
                            "language": language,
                            "exists": True,
                        })

            files["other_subtitles"] = other_subtitles

            return MediaFilesResponse(
                success=True,
                data={
                    "media_id": media_id,
                    "directory_path": media.directory_path,
                    "files": files,
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{media_id}/poster")
async def get_media_poster(media_id: int):
    """
    Serve media poster image.

    Returns the poster image file with proper caching headers.
    No authentication required for public image access.
    """
    try:
        with get_db_session() as session:
            media = session.query(MediaLibrary).filter(
                MediaLibrary.media_id == media_id
            ).first()

            if not media:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Media not found"
                )

            # Check if poster exists
            if not media.poster_path or not os.path.exists(media.poster_path):
                # Return placeholder or 404
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Poster not found"
                )

            # Determine media type from file extension
            ext = os.path.splitext(media.poster_path)[1].lower()
            media_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
            }
            media_type = media_type_map.get(ext, 'image/jpeg')

            # Return file with caching headers
            return FileResponse(
                media.poster_path,
                media_type=media_type,
                headers={
                    'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
                    'ETag': f'"{media_id}-{os.path.getmtime(media.poster_path)}"',
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
