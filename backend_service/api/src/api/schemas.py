"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# Authentication Schemas
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None


class LogoutResponse(BaseModel):
    success: bool
    message: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    user: Optional[dict] = None


# ============================================================================
# Media Schemas
# ============================================================================

class MediaItem(BaseModel):
    media_id: int
    media_type: str
    title: str
    year: Optional[int] = None
    overview: Optional[str] = None
    tmdb_id: Optional[str] = None
    imdb_id: Optional[str] = None
    cast: Optional[List[str]] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_overview: Optional[str] = None
    video_file_path: str
    subtitle_file_path: Optional[str] = None
    directory_path: str
    existence_status: str
    processing_status: str
    created_at: datetime
    updated_at: datetime


class PaginationInfo(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class MediaListResponse(BaseModel):
    success: bool
    data: dict


class MediaDetailResponse(BaseModel):
    success: bool
    data: MediaItem


class FileInfo(BaseModel):
    path: str
    size_bytes: int
    exists: bool
    language: Optional[str] = None


class MediaFilesResponse(BaseModel):
    success: bool
    data: dict


# ============================================================================
# Task Schemas
# ============================================================================

class TaskItem(BaseModel):
    task_id: int
    media_id: int
    media_title: str
    media_type: str
    season: Optional[int] = None
    episode: Optional[int] = None
    status: str
    retry_count: int
    failure_reason: Optional[str] = None
    worker_assignment: Optional[str] = None
    queued_time: datetime
    started_time: Optional[datetime] = None
    timeout_deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    success: bool
    data: dict


class TaskDetailResponse(BaseModel):
    success: bool
    data: dict


class TaskRetryResponse(BaseModel):
    success: bool
    message: str
    data: dict


class TaskCancelResponse(BaseModel):
    success: bool
    message: str
    data: dict


class TaskTriggerRequest(BaseModel):
    media_id: int


class TaskTriggerResponse(BaseModel):
    success: bool
    message: str
    data: dict


# ============================================================================
# History Schemas
# ============================================================================

class HistoryItem(BaseModel):
    history_id: int
    task_id: int
    media_id: int
    media_title: str
    media_type: str
    season: Optional[int] = None
    episode: Optional[int] = None
    status: str
    processing_duration_seconds: Optional[int] = None
    failure_reason: Optional[str] = None
    error_details: Optional[str] = None
    created_at: datetime


class HistoryListResponse(BaseModel):
    success: bool
    data: dict


class HistoryStatsResponse(BaseModel):
    success: bool
    data: dict


# ============================================================================
# System Status Schemas
# ============================================================================

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    services: dict
    error: Optional[str] = None


class SystemStatusResponse(BaseModel):
    success: bool
    data: dict


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[dict] = None
