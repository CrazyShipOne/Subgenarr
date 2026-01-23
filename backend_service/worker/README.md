# Worker Service

The worker service is responsible for processing video files to generate subtitles using LLM technology, as well as running scheduled tasks for media discovery and cleanup.

## Architecture

The worker service consists of several key modules:

### Main Components

1. **main.py** - Entry point that orchestrates all worker operations
   - Manages concurrent task processing loop
   - Runs scheduled media scanner at regular intervals
   - Runs scheduled cleanup tasks at regular intervals
   - Coordinates all background operations

2. **task_processor.py** - Task acquisition and lifecycle management
   - Acquires tasks from the queue with proper locking
   - Coordinates metadata enrichment and media processing phases
   - Handles task completion and failure tracking

3. **metadata_enrichment.py** - NFO parsing and metadata fetching
   - Parses Jellyfin/Emby NFO files
   - Fetches additional metadata from TMDb and OMDb APIs
   - Updates media library with complete metadata

4. **media_processor.py** - Audio/video extraction and subtitle generation
   - Extracts audio segments with overlap for continuity
   - Captures screenshots for visual context
   - Coordinates LLM processing for each segment
   - Generates final SRT subtitle files

5. **llm_client.py** - OpenAI API integration
   - Sends multimodal requests (audio + images) to LLM
   - Handles retries and error recovery
   - Formats prompts with media metadata

6. **media_scanner.py** - Media library scanner (scheduled task)
   - Recursively scans media directory for NFO files
   - Discovers new video files not yet in database
   - Creates media library entries and processing tasks
   - Runs every SCAN_INTERVAL (default: 1 hour)

7. **cleanup_task.py** - System cleanup operations (scheduled task)
   - Checks media file existence and marks deleted items
   - Handles timed-out tasks and moves to history
   - Archives failed tasks that exceeded retry limits
   - Cleans up temporary directories from completed tasks
   - Runs every CLEANUP_INTERVAL (default: 1 hour)

## Processing Pipeline

### Video Processing Pipeline
1. **Task Acquisition**: Worker polls database for pending/failed tasks
2. **Metadata Enrichment**: Parse NFO and fetch missing metadata from APIs
3. **Workspace Setup**: Create temporary directory for processing
4. **Audio Extraction**: Split video into overlapping audio segments
5. **Screenshot Extraction**: Capture frames for visual context
6. **LLM Processing**: Process each segment with AI to generate transcript
7. **Subtitle Generation**: Combine all segments into SRT file
8. **Cleanup**: Remove temporary files and update database

### Scheduled Tasks Pipeline

**Media Scanner** (runs every SCAN_INTERVAL):
1. Recursively scan /media directory for .nfo files
2. For each NFO found, check if already in database/queue/history
3. If new, parse basic metadata from NFO
4. Find corresponding video file
5. Create MediaLibrary entry and TaskQueue entry
6. Log statistics (new items, already processed, errors)

**Cleanup Task** (runs every CLEANUP_INTERVAL):
1. **Media Existence Check**: Mark media as deleted if directory no longer exists
2. **Timeout Handling**: Move timed-out processing tasks to history
3. **Failed Task Cleanup**: Archive tasks that reached max retry count
4. **Temp Directory Cleanup**: Remove temporary files from old/completed tasks
5. **History Pruning** (optional): Delete old processing history entries

## Configuration

Key environment variables:

### Worker Configuration
- `WORKER_ID`: Unique identifier for this worker instance
- `MAX_CONCURRENT_WORKERS`: Number of parallel tasks (default: 2)
- `WORKER_POLL_INTERVAL`: Polling interval in seconds (default: 30)
- `SCAN_INTERVAL`: Media scanner interval in seconds (default: 3600)
- `CLEANUP_INTERVAL`: Cleanup task interval in seconds (default: 3600)
- `TASK_TIMEOUT`: Maximum task processing time in seconds (default: 7200)
- `MAX_FAILURE_COUNT`: Maximum retry attempts before giving up (default: 3)

### AI Configuration
- `AI_BASE_URL`: LLM API endpoint
- `AI_API_KEY`: API authentication key
- `AI_MODEL`: Model identifier (e.g., gpt-4o)
- `AI_TIMEOUT`: Request timeout in seconds (default: 300)
- `AI_MAX_RETRIES`: Retry attempts for failed requests (default: 3)

### Processing Configuration
- `AUDIO_SEGMENT_DURATION`: Segment length in seconds (default: 300)
- `AUDIO_OVERLAP_DURATION`: Overlap duration in seconds (default: 10)
- `SCREENSHOTS_PER_SEGMENT`: Number of screenshots per segment (default: 10)
- `TARGET_SUBTITLE_LANGUAGE`: ISO language code (default: en)
- `TEMP_CLEANUP_ENABLED`: Auto-cleanup temporary files (default: true)
- `TEMP_RETENTION_HOURS`: Hours to retain temp files (default: 24)

### Metadata API Configuration
- `TMDB_API_KEY`: TMDb API key (optional)
- `OMDB_API_KEY`: OMDb API key (optional)
- `METADATA_API_TIMEOUT`: Timeout for metadata requests (default: 30)

### Directory Paths
- `MEDIA_DIR`: Media library path (default: /media)
- `TEMP_DIR`: Temporary processing directory (default: /tmp)
- `CONFIG_DIR`: Configuration directory (default: /config)
- `DATABASE_PATH`: Database file path (default: /config/media_library.db)

## Docker

Build and run using Docker:

```bash
docker build -t video-worker .
docker run -v /path/to/media:/media \
           -v /path/to/config:/config \
           -v /path/to/tmp:/tmp \
           -e AI_API_KEY=your_key \
           -e AI_BASE_URL=https://api.openai.com/v1 \
           video-worker
```

## Dependencies

- Python 3.11+
- ffmpeg (for audio/video processing)
- SQLAlchemy (database ORM)
- httpx (async HTTP client)
- openai (LLM API client)
