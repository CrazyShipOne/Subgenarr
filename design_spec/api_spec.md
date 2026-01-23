# Video Subtitle Generation System - API Specification

## Overview

This document specifies the RESTful API for the Video Subtitle Generation System. The API is built with FastAPI and follows REST principles with JSON request/response formats.

**Base URL**: `http://localhost:8000/api`

**API Version**: v1

## Table of Contents

1. [Authentication](#authentication)
2. [Media Catalog](#media-catalog)
3. [Task Management](#task-management)
4. [Processing History](#processing-history)
5. [System Status](#system-status)
6. [Error Handling](#error-handling)
7. [Data Models](#data-models)

---

## Authentication

All endpoints except `/auth/login` require authentication via session cookie.

### POST /auth/login

Authenticate user and create session.

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Login successful",
  "user": {
    "username": "string"
  }
}
```

**Response** (401 Unauthorized):
```json
{
  "success": false,
  "error": "Invalid credentials"
}
```

**Session**: Sets `session_id` cookie with `SESSION_EXPIRY` duration.

---

### POST /auth/logout

Destroy current session.

**Request**: No body required (uses session cookie)

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Logout successful"
}
```

**Side Effect**: Clears `session_id` cookie.

---

### GET /auth/status

Check current authentication status.

**Response** (200 OK - Authenticated):
```json
{
  "authenticated": true,
  "user": {
    "username": "string"
  }
}
```

**Response** (200 OK - Not Authenticated):
```json
{
  "authenticated": false
}
```

---

## Media Catalog

### GET /media/movies

List all movies in the media library.

**Query Parameters**:
- `page` (integer, optional, default: 1) - Page number
- `page_size` (integer, optional, default: 20, max: 100) - Items per page
- `search` (string, optional) - Search by title
- `year` (integer, optional) - Filter by year
- `has_subtitle` (boolean, optional) - Filter by subtitle existence

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "media_id": 1,
        "media_type": "movie",
        "title": "The Matrix",
        "year": 1999,
        "overview": "A computer hacker learns...",
        "tmdb_id": "603",
        "imdb_id": "tt0133093",
        "cast": ["Keanu Reeves", "Laurence Fishburne"],
        "video_file_path": "/media/movies/The Matrix (1999)/The Matrix (1999).mkv",
        "subtitle_file_path": "/media/movies/The Matrix (1999)/The Matrix (1999)_en_0.srt",
        "has_poster": true,
        "directory_path": "/media/movies/The Matrix (1999)",
        "existence_status": "exists",
        "processing_status": "completed",
        "created_at": "2026-01-20T10:30:00Z",
        "updated_at": "2026-01-20T15:45:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 150,
      "total_pages": 8
    }
  }
}
```

**Processing Status Values**:
- `completed` - Subtitle generated successfully
- `processing` - Currently being processed
- `pending` - Queued for processing
- `failed` - Processing failed
- `unprocessed` - Not yet queued

---

### GET /media/tvshows

List all TV shows in the media library.

**Query Parameters**:
- `page` (integer, optional, default: 1) - Page number
- `page_size` (integer, optional, default: 20, max: 100) - Items per page
- `search` (string, optional) - Search by title
- `year` (integer, optional) - Filter by year
- `season` (integer, optional) - Filter by season number

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "media_id": 2,
        "media_type": "tv",
        "title": "Breaking Bad",
        "year": 2008,
        "overview": "A high school chemistry teacher...",
        "tmdb_id": "1396",
        "imdb_id": "tt0903747",
        "cast": ["Bryan Cranston", "Aaron Paul"],
        "season": 1,
        "episode": 1,
        "episode_overview": "Diagnosed with terminal lung cancer...",
        "video_file_path": "/media/tv/Breaking Bad/Season 01/Breaking Bad - S01E01.mkv",
        "subtitle_file_path": "/media/tv/Breaking Bad/Season 01/Breaking Bad - S01E01_en_0.srt",
        "has_poster": true,
        "directory_path": "/media/tv/Breaking Bad/Season 01",
        "existence_status": "exists",
        "processing_status": "completed",
        "created_at": "2026-01-20T10:30:00Z",
        "updated_at": "2026-01-20T15:45:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 500,
      "total_pages": 25
    }
  }
}
```

**Note**: Each episode is a separate entry. For a grouped view, use `/media/tvshows/grouped` instead.

---

### GET /media/tvshows/grouped

List TV shows grouped by show title (one entry per show).

**Query Parameters**:
- `page` (integer, optional, default: 1) - Page number
- `page_size` (integer, optional, default: 20, max: 100) - Items per page
- `search` (string, optional) - Search by title
- `year` (integer, optional) - Filter by year

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "media_id": 2,
        "media_type": "tv",
        "title": "Breaking Bad",
        "year": 2008,
        "overview": "A high school chemistry teacher...",
        "tmdb_id": "1396",
        "imdb_id": "tt0903747",
        "cast": ["Bryan Cranston", "Aaron Paul"],
        "season_count": 5,
        "episode_count": 62,
        "has_poster": true,
        "created_at": "2026-01-20T10:30:00Z",
        "updated_at": "2026-01-23T15:45:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 25,
      "total_pages": 2
    }
  }
}
```

**Note**: This endpoint aggregates episodes by show title. Use for displaying show cards in the UI. The `media_id` returned is the first episode's ID for linking to detail page.

---

### GET /media/tvshows/detail/{show_title}

Get detailed hierarchical information for a TV show (seasons → episodes).

**Path Parameters**:
- `show_title` (string, required) - TV show title (URL-encoded)

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "title": "Breaking Bad",
    "media_type": "tv",
    "year": 2008,
    "overview": "A high school chemistry teacher...",
    "tmdb_id": "1396",
    "imdb_id": "tt0903747",
    "cast": ["Bryan Cranston", "Aaron Paul"],
    "has_poster": true,
    "season_count": 5,
    "episode_count": 62,
    "seasons": [
      {
        "season_number": 1,
        "episodes": [
          {
            "media_id": 2,
            "episode_number": 1,
            "episode_overview": "Diagnosed with terminal lung cancer...",
            "video_file_path": "/media/tv/Breaking Bad/Season 01/Breaking Bad - S01E01.mkv",
            "subtitle_file_path": "/media/tv/Breaking Bad/Season 01/Breaking Bad - S01E01_en_0.srt",
            "has_poster": true,
            "processing_status": "completed",
            "created_at": "2026-01-20T10:30:00Z",
            "updated_at": "2026-01-20T15:45:00Z"
          },
          {
            "media_id": 3,
            "episode_number": 2,
            "episode_overview": "Walt and Jesse attempt to tie up loose ends...",
            "video_file_path": "/media/tv/Breaking Bad/Season 01/Breaking Bad - S01E02.mkv",
            "subtitle_file_path": null,
            "has_poster": true,
            "processing_status": "pending",
            "created_at": "2026-01-20T10:35:00Z",
            "updated_at": "2026-01-20T10:35:00Z"
          }
        ]
      },
      {
        "season_number": 2,
        "episodes": [...]
      }
    ]
  }
}
```

**Response** (404 Not Found):
```json
{
  "success": false,
  "error": "TV show not found"
}
```

**Note**: This endpoint provides a hierarchical view for the TV show detail page. Episodes are sorted by season and episode number.

---

### GET /media/{media_id}

Get detailed information for a specific media item.

**Path Parameters**:
- `media_id` (integer, required) - Media library ID

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "media_id": 1,
    "media_type": "movie",
    "title": "The Matrix",
    "year": 1999,
    "overview": "A computer hacker learns from mysterious rebels...",
    "tmdb_id": "603",
    "imdb_id": "tt0133093",
    "cast": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss"],
    "season": null,
    "episode": null,
    "episode_overview": null,
    "video_file_path": "/media/movies/The Matrix (1999)/The Matrix (1999).mkv",
    "nfo_file_path": "/media/movies/The Matrix (1999)/movie.nfo",
    "subtitle_file_path": "/media/movies/The Matrix (1999)/The Matrix (1999)_en_0.srt",
    "has_poster": true,
    "directory_path": "/media/movies/The Matrix (1999)",
    "existence_status": "exists",
    "processing_status": "completed",
    "created_at": "2026-01-20T10:30:00Z",
    "updated_at": "2026-01-20T15:45:00Z"
  }
}
```

**Response** (404 Not Found):
```json
{
  "success": false,
  "error": "Media not found"
}
```

---

### GET /media/{media_id}/files

List all files associated with a media item (video, subtitles, etc.).

**Path Parameters**:
- `media_id` (integer, required) - Media library ID

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "media_id": 1,
    "directory_path": "/media/movies/The Matrix (1999)",
    "files": {
      "video": {
        "path": "/media/movies/The Matrix (1999)/The Matrix (1999).mkv",
        "size_bytes": 8589934592,
        "exists": true
      },
      "nfo": {
        "path": "/media/movies/The Matrix (1999)/movie.nfo",
        "size_bytes": 2048,
        "exists": true
      },
      "generated_subtitle": {
        "path": "/media/movies/The Matrix (1999)/The Matrix (1999)_en_0.srt",
        "size_bytes": 102400,
        "language": "en",
        "exists": true
      },
      "other_subtitles": [
        {
          "path": "/media/movies/The Matrix (1999)/The Matrix (1999).zh.srt",
          "size_bytes": 98304,
          "language": "zh",
          "exists": true
        }
      ]
    }
  }
}
```

**Response** (404 Not Found):
```json
{
  "success": false,
  "error": "Media not found"
}
```

---

### GET /media/{media_id}/poster

Serve media poster image file.

**Path Parameters**:
- `media_id` (integer, required) - Media library ID

**Response** (200 OK):
- **Content-Type**: `image/jpeg`, `image/png` (determined by file extension)
- **Headers**:
  - `Cache-Control: public, max-age=86400` (24 hour cache)
  - `ETag: "{media_id}-{file_mtime}"` (for conditional requests)
- **Body**: Binary image data

**Response** (404 Not Found):
```json
{
  "success": false,
  "error": "Poster not found"
}
```

**Response** (404 Not Found - Media Not Found):
```json
{
  "success": false,
  "error": "Media not found"
}
```

**Note**: This endpoint serves poster images directly from the filesystem. No authentication required for public image access. Images are cached for 24 hours to improve performance.

**Frontend Usage**:
```html
<!-- Direct image tag -->
<img src="/api/media/123/poster" alt="Movie Poster" />

<!-- With error handling -->
<img
  src="/api/media/123/poster"
  alt="Movie Poster"
  onerror="this.src='/placeholder.jpg'"
/>
```

---

## Task Management

### GET /tasks

List all tasks with filtering and pagination.

**Query Parameters**:
- `page` (integer, optional, default: 1) - Page number
- `page_size` (integer, optional, default: 20, max: 100) - Items per page
- `status` (string, optional) - Filter by status: `pending`, `metadata_fetching`, `processing`, `completed`, `failed`
- `media_id` (integer, optional) - Filter by media ID
- `media_type` (string, optional) - Filter by media type: `movie`, `tv`

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "task_id": 42,
        "media_id": 15,
        "media_title": "Inception",
        "media_type": "movie",
        "season": null,
        "episode": null,
        "status": "processing",
        "retry_count": 0,
        "failure_reason": null,
        "worker_assignment": "worker-1",
        "queued_time": "2026-01-23T14:00:00Z",
        "started_time": "2026-01-23T14:05:00Z",
        "timeout_deadline": "2026-01-23T16:05:00Z",
        "created_at": "2026-01-23T14:00:00Z",
        "updated_at": "2026-01-23T14:05:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 5,
      "total_pages": 1
    }
  }
}
```

---

### GET /tasks/{task_id}

Get detailed information for a specific task.

**Path Parameters**:
- `task_id` (integer, required) - Task ID

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "task_id": 42,
    "media_id": 15,
    "media_title": "Inception",
    "media_type": "movie",
    "nfo_file_path": "/media/movies/Inception (2010)/movie.nfo",
    "video_file_path": "/media/movies/Inception (2010)/Inception (2010).mkv",
    "status": "processing",
    "retry_count": 0,
    "failure_reason": null,
    "worker_assignment": "worker-1",
    "queued_time": "2026-01-23T14:00:00Z",
    "started_time": "2026-01-23T14:05:00Z",
    "timeout_deadline": "2026-01-23T16:05:00Z",
    "created_at": "2026-01-23T14:00:00Z",
    "updated_at": "2026-01-23T14:05:00Z"
  }
}
```

**Response** (404 Not Found):
```json
{
  "success": false,
  "error": "Task not found"
}
```

---

### POST /tasks/{task_id}/retry

Retry a failed task.

**Path Parameters**:
- `task_id` (integer, required) - Task ID

**Request Body**: None

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Task queued for retry",
  "data": {
    "task_id": 42,
    "status": "pending",
    "retry_count": 1
  }
}
```

**Response** (400 Bad Request):
```json
{
  "success": false,
  "error": "Task cannot be retried (status: processing)"
}
```

**Response** (404 Not Found):
```json
{
  "success": false,
  "error": "Task not found"
}
```

**Business Logic**:
- Only tasks with status `failed` can be retried
- Resets status to `pending`
- Clears `failure_reason`, `worker_assignment`, `started_time`, `timeout_deadline`
- Increments `retry_count`

---

### POST /tasks/{task_id}/cancel

Cancel a pending or processing task.

**Path Parameters**:
- `task_id` (integer, required) - Task ID

**Request Body**: None

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Task cancelled successfully",
  "data": {
    "task_id": 42,
    "status": "failed",
    "failure_reason": "cancelled_by_user"
  }
}
```

**Response** (400 Bad Request):
```json
{
  "success": false,
  "error": "Task cannot be cancelled (status: completed)"
}
```

**Response** (404 Not Found):
```json
{
  "success": false,
  "error": "Task not found"
}
```

**Business Logic**:
- Only tasks with status `pending`, `metadata_fetching`, or `processing` can be cancelled
- Sets status to `failed`
- Sets `failure_reason` to `cancelled_by_user`
- Removes task from queue and moves to processing history

---

### POST /tasks/trigger

Manually trigger processing for a specific media item.

**Request Body**:
```json
{
  "media_id": 15
}
```

**Response** (200 OK - Task Created):
```json
{
  "success": true,
  "message": "Task created successfully",
  "data": {
    "task_id": 43,
    "media_id": 15,
    "status": "pending"
  }
}
```

**Response** (200 OK - Task Already Exists):
```json
{
  "success": true,
  "message": "Task already exists",
  "data": {
    "task_id": 42,
    "media_id": 15,
    "status": "processing"
  }
}
```

**Response** (400 Bad Request):
```json
{
  "success": false,
  "error": "Media already has subtitle"
}
```

**Response** (404 Not Found):
```json
{
  "success": false,
  "error": "Media not found"
}
```

**Business Logic**:
- Check if media exists and has no subtitle
- Check if task already exists in queue for this media
- If no task exists, create new task with status `pending`
- If task exists, return existing task info

---

## Processing History

### GET /history

List processing history with filtering and pagination.

**Query Parameters**:
- `page` (integer, optional, default: 1) - Page number
- `page_size` (integer, optional, default: 20, max: 100) - Items per page
- `status` (string, optional) - Filter by status: `success`, `failed`
- `media_id` (integer, optional) - Filter by media ID
- `media_type` (string, optional) - Filter by media type: `movie`, `tv`
- `search` (string, optional) - Search by media title
- `date_from` (string, optional, ISO 8601) - Filter by date range start
- `date_to` (string, optional, ISO 8601) - Filter by date range end

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "history_id": 123,
        "task_id": 42,
        "media_id": 15,
        "media_title": "Inception",
        "media_type": "movie",
        "season": null,
        "episode": null,
        "status": "success",
        "processing_duration_seconds": 3600,
        "failure_reason": null,
        "error_details": null,
        "created_at": "2026-01-23T15:05:00Z"
      },
      {
        "history_id": 122,
        "task_id": 41,
        "media_id": 14,
        "media_title": "The Dark Knight",
        "media_type": "movie",
        "season": null,
        "episode": null,
        "status": "failed",
        "processing_duration_seconds": 120,
        "failure_reason": "llm_api_error",
        "error_details": "API request timeout after 300 seconds",
        "created_at": "2026-01-23T14:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 150,
      "total_pages": 8
    }
  }
}
```

---

### GET /history/stats

Get processing statistics.

**Query Parameters**:
- `date_from` (string, optional, ISO 8601) - Filter by date range start
- `date_to` (string, optional, ISO 8601) - Filter by date range end

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "total_processed": 150,
    "successful": 135,
    "failed": 15,
    "success_rate": 0.90,
    "average_duration_seconds": 3200,
    "total_duration_seconds": 480000,
    "failure_reasons": {
      "llm_api_error": 8,
      "timeout": 4,
      "audio_extraction_error": 2,
      "cancelled_by_user": 1
    },
    "processing_by_date": [
      {
        "date": "2026-01-23",
        "total": 10,
        "successful": 9,
        "failed": 1
      },
      {
        "date": "2026-01-22",
        "total": 15,
        "successful": 14,
        "failed": 1
      }
    ]
  }
}
```

---

## System Status

### GET /health

Health check endpoint for monitoring.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2026-01-23T15:47:38Z",
  "services": {
    "database": "healthy",
    "worker": "healthy"
  }
}
```

**Response** (503 Service Unavailable):
```json
{
  "status": "unhealthy",
  "timestamp": "2026-01-23T15:47:38Z",
  "services": {
    "database": "unhealthy",
    "worker": "healthy"
  },
  "error": "Database connection failed"
}
```

---

### GET /status

Get system status and statistics.

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "system": {
      "version": "1.0.0",
      "uptime_seconds": 86400,
      "current_time": "2026-01-23T15:47:38Z"
    },
    "queue": {
      "pending": 5,
      "metadata_fetching": 1,
      "processing": 2,
      "failed": 3,
      "total": 11
    },
    "workers": {
      "max_concurrent": 2,
      "active": 2,
      "workers": [
        {
          "worker_id": "worker-1",
          "status": "busy",
          "current_task_id": 42,
          "started_at": "2026-01-23T14:05:00Z"
        },
        {
          "worker_id": "worker-2",
          "status": "busy",
          "current_task_id": 43,
          "started_at": "2026-01-23T14:10:00Z"
        }
      ]
    },
    "media": {
      "total": 650,
      "movies": 150,
      "tv_episodes": 500,
      "with_subtitles": 135,
      "without_subtitles": 515
    },
    "storage": {
      "temp_directory": "/tmp",
      "temp_usage_mb": 2048,
      "database_size_mb": 50
    }
  }
}
```

---

## Error Handling

### Standard Error Response Format

All error responses follow this format:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "Additional context"
  }
}
```

### HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Error Codes

| Error Code | Description |
|------------|-------------|
| `AUTH_INVALID_CREDENTIALS` | Invalid username or password |
| `AUTH_SESSION_EXPIRED` | Session has expired |
| `AUTH_REQUIRED` | Authentication required |
| `VALIDATION_ERROR` | Request validation failed |
| `RESOURCE_NOT_FOUND` | Requested resource not found |
| `RESOURCE_ALREADY_EXISTS` | Resource already exists |
| `INVALID_STATE` | Operation not allowed in current state |
| `DATABASE_ERROR` | Database operation failed |
| `EXTERNAL_API_ERROR` | External API call failed |
| `INTERNAL_ERROR` | Internal server error |

### Validation Error Response

```json
{
  "success": false,
  "error": "Validation error",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "fields": [
      {
        "field": "page_size",
        "message": "Must be between 1 and 100"
      }
    ]
  }
}
```

---

## Example Workflows

### Workflow 1: User Login and View Movies

1. `POST /api/auth/login` - Authenticate
2. `GET /api/media/movies?page=1&page_size=20` - Get movie list
3. `GET /api/media/{media_id}` - View movie details
4. `GET /api/media/{media_id}/files` - View associated files

### Workflow 2: Manual Task Trigger

1. User navigates to media detail page
2. Frontend checks if subtitle exists
3. If not, show "Generate Subtitle" button
4. User clicks button
5. `POST /api/tasks/trigger` with `media_id`
6. Frontend polls `GET /api/tasks?media_id={media_id}` every 30s
7. When task completes, refresh media details

### Workflow 3: View Processing History

1. `GET /api/history/stats` - Get statistics for dashboard
2. `GET /api/history?page=1&status=failed` - View failed tasks
3. Click on history item to view error details

### Workflow 4: Retry Failed Task

1. `GET /api/tasks?status=failed` - List failed tasks
2. User clicks "Retry" button
3. `POST /api/tasks/{task_id}/retry`
4. Task status changes to `pending`
5. Worker picks up task automatically
