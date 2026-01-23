# Video Subtitle Generation System

An automated subtitle generation system for TV shows and movies using LLM technology. The system scans media directories, extracts audio and video frames, and generates accurate subtitles through AI analysis.

## Features

- 🎬 **Automatic Media Discovery**: Scans media directories for movies and TV shows with NFO files (Jellyfin/Emby format)
- 🤖 **AI-Powered Subtitle Generation**: Uses multimodal LLM (audio + video frames) for accurate transcription
- 🌐 **Web Interface**: Modern Vue 3 frontend with responsive design
- 📊 **Task Management**: Monitor processing tasks, retry failed jobs, and view history
- 🎨 **Poster Images**: Display movie/TV show posters in the UI
- 🌍 **Multilingual**: Support for English and Chinese interfaces
- 🔄 **Background Processing**: Separate worker service for non-blocking operations
- 📈 **Statistics Dashboard**: Track success rates and processing performance

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Frontend  │─────▶│  Backend API │◀────▶│  SQLite Database│
│  (Vue 3)    │      │  (FastAPI)   │      │                 │
└─────────────┘      └──────────────┘      └─────────────────┘
                            │
                            ▼
                     ┌──────────────┐      ┌─────────────────┐
                     │    Worker    │─────▶│  Media Files    │
                     │  (Python)    │      │  (NFO, Videos)  │
                     └──────────────┘      └─────────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  LLM API     │
                     │  (OpenAI)    │
                     └──────────────┘
```

## Prerequisites

- Docker and Docker Compose
- Media files organized with NFO files (Jellyfin/Emby/Plex format)
- TMDb API key (https://www.themoviedb.org/settings/api)
- OMDb API key (http://www.omdbapi.com/apikey.aspx)
- OpenAI-compatible LLM API (OpenAI, Azure OpenAI, vLLM, Ollama, etc.)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd video_analysis
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
nano .env  # Edit with your configuration
```

Key configurations to set:
- `AUTH_USERNAME` and `AUTH_PASSWORD`: Admin credentials
- `AI_BASE_URL` and `AI_API_KEY`: Your LLM API endpoint and key
- `AI_MODEL`: Model name (e.g., gpt-4o, gpt-4-vision-preview)
- `TMDB_API_KEY` and `OMDB_API_KEY`: Metadata API keys

### 3. Prepare Media Directory

Organize your media files with NFO files:

```
media/
├── movies/
│   └── The Matrix (1999)/
│       ├── The Matrix (1999).mkv
│       ├── movie.nfo
│       └── poster.jpg
└── tv/
    └── Breaking Bad/
        ├── Season 01/
        │   ├── Breaking Bad - S01E01.mkv
        │   ├── Breaking Bad - S01E01.nfo
        │   └── poster.jpg
        └── poster.jpg
```

### 4. Initialize Database

Create the database schema:

```bash
mkdir -p config
sqlite3 config/media_library.db < database/schema.sql
```

### 5. Start Services

```bash
docker-compose up -d
```

This will start three services:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Worker**: Background processing service

### 6. Access the Application

1. Open http://localhost:3000 in your browser
2. Login with credentials from `.env` file
3. Wait for media scanning to complete (runs every hour by default)
4. View discovered media and trigger subtitle generation

## Configuration

### Environment Variables

See `.env.example` for all available configuration options.

#### AI Configuration

```bash
# OpenAI
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-...
AI_MODEL=gpt-4o

# Azure OpenAI
AI_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
AI_API_KEY=your-azure-key
AI_MODEL=gpt-4-vision

# Ollama (Local)
AI_BASE_URL=http://localhost:11434/v1
AI_API_KEY=ollama
AI_MODEL=llava
```

#### Scheduling

- `SCAN_INTERVAL`: How often to scan for new media (default: 3600s = 1 hour)
- `CLEANUP_INTERVAL`: How often to clean up stale tasks (default: 3600s = 1 hour)
- `WORKER_POLL_INTERVAL`: How often worker checks for tasks (default: 30s)
- `TASK_TIMEOUT`: Maximum processing time per task (default: 7200s = 2 hours)

#### Processing

- `MAX_CONCURRENT_WORKERS`: Number of parallel workers (default: 2)
- `AUDIO_SEGMENT_DURATION`: Audio chunk size in seconds (default: 300s = 5 minutes)
- `SCREENSHOTS_PER_SEGMENT`: Number of screenshots per audio segment (default: 10)
- `TARGET_SUBTITLE_LANGUAGE`: Output language code (default: en)

### Volume Mounts

Configure these paths in `docker-compose.yml`:

- `./media:/media` - Your media library (movies and TV shows)
- `./config:/config` - Database and configuration storage
- `./tmp:/tmp` - Temporary processing files

## Usage

### Web Interface

#### Movies Page
- Browse movies in grid or list view
- Search by title, filter by year or subtitle status
- Click on a movie to view details and files

#### TV Shows Page
- Shows grouped by series title
- View season and episode counts
- Click to see hierarchical season/episode view

#### Task List
- Monitor active and pending subtitle generation tasks
- Retry failed tasks
- Cancel running tasks
- Auto-refreshes every 30 seconds

#### Processing History
- View statistics dashboard
- Search and filter processing history
- Expand failed items to see error details

### Manual Subtitle Generation

1. Navigate to a movie or TV episode detail page
2. If no subtitle exists, click "Generate Subtitle" button
3. Task will be queued and processed by the worker
4. Monitor progress in the Task List page

### API Documentation

Access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Project Structure

```
video_analysis/
├── backend_service/
│   ├── api/              # FastAPI backend
│   ├── worker/           # Background worker
│   └── shared/           # Shared models and utilities
├── frontend_page/         # Vue 3 frontend
├── database/             # Database schema
├── design_spec/          # Design specifications
├── docker-compose.yml    # Service orchestration
└── .env.example          # Environment configuration template
```

### Running in Development Mode

#### Backend API
```bash
cd backend_service/api
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

#### Worker
```bash
cd backend_service/worker
pip install -r requirements.txt
python -m src.worker.main
```

#### Frontend
```bash
cd frontend_page
npm install
npm run dev  # Runs on http://localhost:5173
```

## Troubleshooting

### Media Not Appearing

1. Check that NFO files are present and valid XML
2. Wait for media scan to complete (check logs)
3. Verify `media` volume mount in docker-compose.yml
4. Check worker logs: `docker logs video-subtitle-worker`

### Subtitle Generation Failing

1. Verify AI API credentials and endpoint
2. Check worker logs for error details
3. Ensure FFmpeg can access video files
4. Verify sufficient disk space in `/tmp`

### Database Locked Errors

1. Ensure only one worker instance is running
2. Check that SQLite is using WAL mode
3. Increase busy_timeout if needed

### Poster Images Not Loading

1. Verify poster files exist (poster.jpg, folder.jpg, etc.)
2. Check file permissions
3. Verify poster_path in database
4. Check API logs for 404 errors

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/status` - Check authentication status

### Media
- `GET /api/media/movies` - List movies
- `GET /api/media/tvshows/grouped` - List TV shows (grouped)
- `GET /api/media/tvshows/detail/{title}` - TV show details
- `GET /api/media/{media_id}` - Media details
- `GET /api/media/{media_id}/poster` - Poster image

### Tasks
- `GET /api/tasks` - List tasks
- `POST /api/tasks/trigger` - Trigger subtitle generation
- `POST /api/tasks/{task_id}/retry` - Retry failed task
- `POST /api/tasks/{task_id}/cancel` - Cancel task

### History
- `GET /api/history` - Processing history
- `GET /api/history/stats` - Statistics

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please follow the existing code style and include tests for new features.

## Support

For issues and questions:
- Check the troubleshooting section above
- Review API logs: `docker logs video-subtitle-api`
- Review worker logs: `docker logs video-subtitle-worker`
- Open an issue on GitHub
