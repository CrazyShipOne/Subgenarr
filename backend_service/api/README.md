# API Service

The API service provides a RESTful HTTP interface for managing media, tasks, and system status.

## Architecture

### Main Components

1. **main.py** - FastAPI application entry point
   - Configures CORS, exception handling
   - Registers all route handlers
   - Initializes database on startup

2. **routes/** - API endpoint handlers
   - **auth.py**: Authentication endpoints (login, logout, status)
   - **media.py**: Media catalog endpoints (movies, TV shows, details, files)
   - **tasks.py**: Task management endpoints (list, retry, cancel, trigger)
   - **history.py**: Processing history endpoints (list, statistics)
   - **system.py**: System status endpoints (health, status)

3. **middleware/auth.py** - Authentication middleware
   - Session validation
   - User authentication dependencies

4. **schemas.py** - Pydantic models for request/response validation

5. **utils/auth.py** - Authentication utilities
   - Password hashing
   - Session management

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/status` - Check authentication status

### Media Catalog
- `GET /api/media/movies` - List movies with pagination and filters
- `GET /api/media/tvshows` - List TV shows with pagination and filters
- `GET /api/media/{media_id}` - Get media details
- `GET /api/media/{media_id}/files` - List associated files

### Task Management
- `GET /api/tasks` - List tasks with filters
- `GET /api/tasks/{task_id}` - Get task details
- `POST /api/tasks/{task_id}/retry` - Retry failed task
- `POST /api/tasks/{task_id}/cancel` - Cancel task
- `POST /api/tasks/trigger` - Manually trigger processing

### Processing History
- `GET /api/history` - List processing history
- `GET /api/history/stats` - Get processing statistics

### System Status
- `GET /api/health` - Health check (no auth required)
- `GET /api/status` - System status and statistics

## Authentication

The API uses session-based authentication with HTTP-only cookies:

1. Client sends credentials to `/api/auth/login`
2. Server validates and returns `session_id` cookie
3. Client includes cookie in subsequent requests
4. Server validates session and extracts user info

Session configuration:
- `SESSION_SECRET`: Secret key for session encryption
- `SESSION_EXPIRY`: Session duration in seconds (default: 24 hours)

## Configuration

Key environment variables:

### Authentication
- `AUTH_USERNAME`: Admin username (default: admin)
- `AUTH_PASSWORD`: Admin password (default: admin)
- `SESSION_SECRET`: Session encryption key
- `SESSION_EXPIRY`: Session expiration in seconds (default: 86400)

### Network
- `BACKEND_PORT`: API service port (default: 8000)

### Database
- `DATABASE_PATH`: SQLite database path (default: /config/media_library.db)
- `CONFIG_DIR`: Configuration directory (default: /config)

## Running the API

### Development
```bash
cd backend_service/api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker
```bash
docker build -t video-api .
docker run -p 8000:8000 \
           -v /path/to/config:/config \
           -e AUTH_USERNAME=admin \
           -e AUTH_PASSWORD=secure_password \
           -e SESSION_SECRET=your_secret_key \
           video-api
```

## API Documentation

Once running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Error Handling

All endpoints return standardized error responses:

```json
{
  "success": false,
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "details": {}
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `500`: Internal Server Error
- `503`: Service Unavailable

## Dependencies

- Python 3.11+
- FastAPI (web framework)
- Uvicorn (ASGI server)
- SQLAlchemy (database ORM)
- Pydantic (data validation)
