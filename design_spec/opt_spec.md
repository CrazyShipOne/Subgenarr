# Video Subtitle Generation System - Optimized Specification

## Project Overview

An automated subtitle generation system for TV shows and movies using LLM technology. The system scans media directories, extracts audio and video frames, and generates accurate subtitles through AI analysis.

## Project File Structure

```
video_analysis/
├── backend_service/
|   ├── api
│   |   ├── src/
│   |   │   ├── api/
│   |   │   │   └── (API endpoints and routes)
│   |   │   ├── models/
│   |   │   │   └── (database models)
│   |   │   ├── utils/
│   |   │   │   └── (shared utilities)
│   |   │   └── (other shared modules)
│   |   └── Dockerfile
├   ├── worker/
│   |   ├── src/
│   |   │   ├── worker/
│   |   │   │   └── (worker processing logic)
│   |   │   ├── prompts/
│   |   │   │   └── transcription.txt
│   |   │   └── (other worker modules)
│   |   └── Dockerfile
│   └── shared/
│       └── (shared code between API and Worker, e.g., database schema, common utilities)
├── frontend_page/
│   ├── src/
│   └── (other files and directories)
│   └── Dockerfile
├── design_spec/
│   └── (specification and design documents)
├── docker-compose.yml
├── README.md
└── LICENSE
```

## Architecture Overview

### Technology Stack
- **Frontend**: Vue 3 + TypeScript + Tailwind CSS
- **Backend**: Python 3.11+ with FastAPI
- **Database**: SQLite for persistence
- **Task Processing**: Asynchronous task queue with worker pool
- **Deployment**: Docker Compose with multi-container architecture

### Container Architecture
Three-service architecture:
1. **Frontend Service**: Serves the Vue application
2. **Backend API Service**: Handles HTTP requests and coordinates tasks
3. **Worker Service**: Processes video/audio extraction and LLM calls independently

**Optimization Rationale**: Separating the worker from the API service allows better resource isolation, prevents API blocking during heavy processing, and enables independent scaling.

## Deployment Configuration

### Docker Setup
- Dockerfile for frontend (Node-based build + Nginx)
- Dockerfile for backend API
- Dockerfile for worker service (shares backend codebase)
- docker-compose.yml orchestrating all services

### Volume Mounts
1. `/media` - Media library path (example: `/media/tv:/path/to/tvseries`)
2. `/tmp` - Temporary processing directory
3. `/config` - Configuration and SQLite database storage

**Note**: Logs are sent to stdout/stderr for Docker best practices. Users can configure log persistence in docker-compose if needed.

### Environment Variables

#### AI Configuration
- `AI_BASE_URL` - LLM API endpoint
- `AI_API_KEY` - Authentication key for LLM API
- `AI_MODEL` - Model name/identifier
- `AI_TIMEOUT` - Request timeout (default: 300s)
- `AI_MAX_RETRIES` - Retry attempts for failed requests (default: 3)

#### Metadata API Configuration
- `TMDB_API_KEY` - TMDb API key for fetching movie/TV metadata
- `OMDB_API_KEY` - OMDb API key (alternative/fallback source)
- `METADATA_API_TIMEOUT` - Timeout for metadata API requests (default: 30s)

**Optimization**: Added timeout and retry configuration for resilience.

#### Network Configuration
- `HTTP_PROXY` - HTTP proxy for external requests
- `FRONTEND_PORT` - Frontend service port (default: 3000)
- `BACKEND_PORT` - Backend API port (default: 8000)

#### Authentication
- `AUTH_USERNAME` - Admin username
- `AUTH_PASSWORD` - Admin password (will be hashed in database)
- `SESSION_SECRET` - Secret key for session encryption
- `SESSION_EXPIRY` - Session expiration time (default: 24h)

#### Scheduling Configuration
- `SCAN_INTERVAL` - Media scanning interval (default: 1h)
- `CLEANUP_INTERVAL` - Cleanup task interval (default: 1h)
- `WORKER_POLL_INTERVAL` - Worker polling interval (default: 30s)
- `TASK_TIMEOUT` - Maximum task processing time (default: 2h)

**Optimization**: Changed from "processing task interval" to "worker poll interval" for clearer semantics.

#### Processing Configuration
- `MAX_FAILURE_COUNT` - Maximum retry attempts before giving up (default: 3)
- `MAX_CONCURRENT_WORKERS` - Number of parallel worker processes (default: 2)
- `AUDIO_SEGMENT_DURATION` - Audio chunk length (default: 5m)
- `AUDIO_OVERLAP_DURATION` - Overlap between chunks (default: 10s)
- `SCREENSHOTS_PER_SEGMENT` - Screenshots per audio segment (default: 10)
- `TARGET_SUBTITLE_LANGUAGE` - ISO language code (default: en)
- `TEMP_CLEANUP_ENABLED` - Auto-cleanup temporary files (default: true)
- `TEMP_RETENTION_HOURS` - Hours to retain temp files for debugging (default: 24h)

**Optimization**: Added temp cleanup configuration for disk space management.

## Data Model Design

### Core Tables

#### 1. Media Library Table
Stores discovered media metadata and current state.

**Key Fields**:
- Unique identifiers (database ID, TMDB/IMDB ID)
- Media type (movie/tv show)
- Metadata (title, year, overview, season, episode, episode overview, cast)
- File paths (video file, NFO file, subtitle file, directory path)
- Existence status (exists/deleted)
- Timestamps (created, updated)

**Optimization**: Separated from task queue to maintain a clean catalog independent of processing state. Subtitle file path is stored here since each video will only be processed once successfully.

#### 2. Task Queue Table
Tracks items pending or in-progress processing.

**Key Fields**:
- Task ID (primary key)
- Media reference (foreign key to Media Library)
- File paths (NFO, video)
- Status enum
- Retry count and failure reason
- Worker assignment identifier
- Timing info (queued time, started time, timeout deadline)
- Timestamps (created, updated)

**Status Values**: `pending`, `metadata_fetching`, `processing`, `completed`, `failed`

**Optimization**:
- Added worker assignment to track which worker is handling the task
- Simplified status enum for clearer state machine
- Removed priority field (not needed per user feedback - processing is per-video only)

#### 3. Processing History Table
Immutable audit log of all processing attempts.

**Key Fields**:
- History ID (primary key)
- Task reference (task ID from queue)
- Media reference (foreign key to Media Library)
- Status (success/failed)
- Processing duration
- Failure details and error messages
- Timestamps (created, updated)

**Optimization**: Separate history table for audit trail without cluttering the active queue.

### Indexes & Constraints
- Foreign keys between tables for referential integrity
- Indexes on: media paths, task status, timestamps for efficient queries
- Unique constraints on media identifiers

### Database Configuration & Concurrency

Since the API service and Worker service run in separate containers accessing the same SQLite database, proper configuration is needed for concurrent access:

- Enable **WAL (Write-Ahead Logging) mode** via `PRAGMA journal_mode=WAL`
- Configure `busy_timeout` parameter to handle temporary locks
- Set appropriate connection pool sizes for each service
- Implement retry logic for database lock errors

## Backend Module Design

### API Layer
RESTful API with FastAPI framework providing:

**Authentication Endpoints**:
- `POST /api/auth/login` - Validate credentials and create session
- `POST /api/auth/logout` - Destroy current session
- `GET /api/auth/status` - Check authentication status

**Media Catalog Endpoints**:
- `GET /api/media/movies` - List all movies with pagination
- `GET /api/media/tvshows` - List all TV episodes with pagination (flat list)
- `GET /api/media/tvshows/grouped` - List TV shows grouped by title (one entry per show)
- `GET /api/media/tvshows/detail/{show_title}` - Get TV show with hierarchical seasons/episodes
- `GET /api/media/{media_id}` - Get detailed media information (for movies or single episodes)
- `GET /api/media/{media_id}/files` - List all files (video, subtitles) for a media item
- `GET /api/media/{media_id}/poster` - Serve poster image file

**Task Management Endpoints**:
- `GET /api/tasks` - List all tasks with filtering
- `GET /api/tasks/{task_id}` - Get task details
- `POST /api/tasks/{task_id}/retry` - Retry a failed task
- `POST /api/tasks/{task_id}/cancel` - Cancel a running task
- `POST /api/tasks/trigger` - Manually trigger processing for a specific media item

**Processing History Endpoints**:
- `GET /api/history` - List processing history with pagination and filtering
- `GET /api/history/stats` - Get success/failure statistics

**System Status Endpoints**:
- `GET /api/health` - Health check for monitoring
- `GET /api/status` - System status (active workers, queue size, etc.)

**Optimization**: Added manual trigger endpoint for user-initiated processing and system status for observability.

### Scheduled Tasks Module

#### 1. Media Scanner Task
Runs every `SCAN_INTERVAL` (default: 1h)

**Process**:
1. Recursively scan `/media` directory for NFO files (Jellyfin/Emby format)
2. For each discovered NFO file:
   - Extract video file path (same directory, matching basename)
   - Check if already processed:
     - Query Task Queue Table for matching NFO path
     - Query Processing History Table for matching NFO path
   - If not found in either table:
     - Parse basic info from NFO (media type, identifiers)
     - Create entry in Media Library Table (status: exists)
     - Insert new task in Task Queue Table (status: pending)
3. Log scan results (new items discovered, total items)

**NFO Parsing**: Use XML parser to extract Jellyfin/Emby NFO format (compatible with Sonarr/Radarr)

**Optimization**: Scanner only creates tasks, doesn't process them - cleaner separation of concerns.

#### 2. Cleanup Task
Runs every `CLEANUP_INTERVAL` (default: 1h)

**Process**:
1. **Media Existence Check**:
   - Query all entries in Media Library Table with status "exists"
   - For each entry, check if directory path still exists
   - If not exists: Update status to "deleted"

2. **Timeout Handling**:
   - Query Task Queue for tasks with status "processing"
   - Check if `started_time + TASK_TIMEOUT` < current_time
   - For timed-out tasks:
     - Remove from Task Queue Table
     - Insert into Processing History Table (status: failed, reason: "timeout")

3. **Failed Task Cleanup**:
   - Query Task Queue for tasks with status "failed" and retry_count >= MAX_FAILURE_COUNT
   - For each failed task:
     - Remove from Task Queue Table
     - Insert into Processing History Table (status: failed, reason: "{status}_{failure_reason}")

4. **Temporary Directory Cleanup**:
   - List directories in `/tmp` matching pattern `{task_id}_*`
   - For each directory:
     - Check if corresponding task still exists in Task Queue
     - If not (completed/failed), and directory age > TEMP_RETENTION_HOURS:
       - Delete directory and contents

5. **History Pruning** (optional):
   - If configured, delete Processing History entries older than retention period

**Optimization**: Added temp directory cleanup and history pruning for disk management.

### Worker Service Module

The worker service runs as a separate container, continuously polling for tasks.

#### Main Worker Loop
**Process**:
1. Poll Task Queue Table every `WORKER_POLL_INTERVAL`
2. Check current active workers count
3. If count < `MAX_CONCURRENT_WORKERS`:
   - Acquire next available task
   - Spawn async task to process it
4. Sleep until next poll interval

#### Task Acquisition
**Process**:
1. Query Task Queue for tasks with status in (`pending`, `metadata_fetching`, `failed`)
2. Filter:
   - Status is `pending` OR
   - Status is `failed` with retry_count < MAX_FAILURE_COUNT
3. Order by: created_time ASC (FIFO)
4. Acquire database lock on the task row
5. Update task:
   - Set worker_assignment to current worker ID
   - Set started_time to current time
   - Set timeout_deadline to current_time + TASK_TIMEOUT
6. Return task details

#### Metadata Enrichment Phase
**Process**:
1. Update task status to `metadata_fetching`
2. Parse NFO file (Jellyfin/Emby XML format):
   - Extract: TMDB/IMDB ID, title, year, overview, season (if TV), episode (if TV), episode overview, cast
3. Check if metadata is complete:
   - Required fields: title, year, overview
   - For TV shows: season, episode, episode overview
4. If incomplete:
   - Query TMDb API using TMDB ID or search by title+year
   - If TMDb fails, fallback to OMDb API
   - Extract missing metadata fields
5. Update Media Library Table with complete metadata
6. **On Success**:
   - Advance task status to `processing`
   - Reset retry_count to 0
7. **On Failure**:
   - Update task status to `failed`
   - Increment retry_count
   - Set failure_reason with error details

**Error Handling**: Catch and categorize errors (network, parsing, API limits, etc.)

#### Media Processing Phase
**Process**:

**Step 1: Workspace Setup**
- Create temp directory: `/tmp/{task_id}_{6_random_chars}/`
- Create subdirectories: `audio/`, `screenshots/`

**Step 2: Audio Extraction**
- Use ffmpeg to extract audio from video file
- Split into segments:
  - Segment 0: 0s to AUDIO_SEGMENT_DURATION
  - Segment N: (N * AUDIO_SEGMENT_DURATION - AUDIO_OVERLAP_DURATION) to ((N+1) * AUDIO_SEGMENT_DURATION)
  - Continue until end of video
- Save each segment as: `audio/{n}/audio.wav` (n = segment index, starting from 0)
- Store segment metadata: start_time, end_time, duration

**Step 3: Frame Extraction**
- For each audio segment:
  - Calculate time range: segment_start_time to segment_end_time
  - Extract SCREENSHOTS_PER_SEGMENT frames evenly distributed across the range
  - Save frames as: `screenshots/{n}/0.jpg`, `screenshots/{n}/1.jpg`, etc.
  - Frame indices: 0 to (SCREENSHOTS_PER_SEGMENT - 1)

**Step 4: LLM Processing Loop**
- Initialize: previous_overlap_text = ""
- For each segment index (0 to N):

  **4a. Load Prompt Template**:
  - Read prompt template from `backend_worker/src/prompts/transcription.txt`
  - Fill placeholders with:
    - Media metadata (title, year, overview, cast, episode info)
    - Target language: TARGET_SUBTITLE_LANGUAGE
    - Previous overlap text (if any)
    - Instructions to output timestamped transcript

  **4b. Prepare Message**:
  - Load audio file: `audio/{segment_index}/audio.wav`
  - Load all screenshot files from: `screenshots/{segment_index}/`
  - Construct multimodal message with: prompt text, audio data, image data

  **4c. Call LLM API**:
  - Use OpenAI SDK with AI_BASE_URL, AI_API_KEY, AI_MODEL
  - Set timeout: AI_TIMEOUT
  - Retry logic: AI_MAX_RETRIES attempts with exponential backoff
  - Expect response format: timestamped transcript lines like "[HH:MM:SS - HH:MM:SS] text"

  **4d. Parse LLM Response**:
  - Extract transcript lines with timestamps
  - Each line format: "[start_time - end_time] subtitle_text"

  **4e. Adjust Timestamps**:
  - Convert relative timestamps to absolute:
    - LLM returns: "[00:00:30 - 00:00:38] Good morning"
    - Segment starts at: 300s (5 minutes)
    - Adjusted: "[00:05:30 - 00:05:38] Good morning"
  - Formula: absolute_time = segment_start_time + relative_time

  **4f. Handle Overlap**:
  - Check if any transcript lines fall within the overlap region:
    - Overlap region: segment_end_time - AUDIO_OVERLAP_DURATION to segment_end_time
  - If lines found in overlap:
    - Extract those lines as `previous_overlap_text` for next iteration
    - Remove them from current segment's output (to avoid duplication)
  - If this is the last segment, don't remove overlap lines

  **4g. Append to Output**:
  - Append adjusted transcript lines to: `{temp_dir}/transcripts.txt`
  - Format: One line per subtitle with adjusted timestamps

**Step 5: Subtitle Generation**
- Read `{temp_dir}/transcripts.txt`
- Convert to SRT format:
  - Sequential numbering (1, 2, 3, ...)
  - Timestamp format: HH:MM:SS,mmm --> HH:MM:SS,mmm
  - Subtitle text
  - Blank line separator
- Generate output filename:
  - Pattern: `{video_filename}_{language_code}_{index}.srt`
  - Start with index = 0
  - Check if file exists in video directory, increment index if needed
- Write SRT file to video directory

**Step 6: Task Completion**
- Update Media Library Table:
  - Set subtitle_file_path to the generated SRT file path
- Remove task from Task Queue Table
- Insert record into Processing History Table:
  - status: "success"
  - processing_duration: end_time - started_time
- Clean up temp directory (if TEMP_CLEANUP_ENABLED)

**Error Handling**:
- Wrap each step in try-catch
- On error:
  - Update task status to `failed`
  - Increment retry_count
  - Set failure_reason with step name and error message
  - Log error details
  - Clean up partial temp files

### External API Integration Module

#### TMDb/OMDb Client
- Wrapper functions for metadata fetching
- Rate limiting to respect API quotas
- Caching layer to reduce redundant requests (in-memory cache with TTL)
- Proxy support via HTTP_PROXY environment variable
- Timeout handling via METADATA_API_TIMEOUT
- Retry logic with exponential backoff

#### OpenAI SDK Wrapper
- Configure base URL and API key from environment
- Multimodal message construction (audio + images + text)
- Timeout configuration
- Retry logic with exponential backoff
- Error parsing and categorization
- Proxy support via HTTP_PROXY

**Optimization**: Centralized external API clients with resilience patterns built-in.

## Frontend Design

### Layout Structure
- Responsive design with collapsible sidebar (left side, 15% width when expanded)
- Top navigation bar:
  - Left: Sidebar collapse/expand button
  - Right: Language selector dropdown, Logout button
- Main content area (85% width, switches based on sidebar menu selection)
- Default view: Movies page

### Page Components

#### 1. Login Page
**Layout**:
- Simple centered form with username and password inputs
- Submit button (disabled until both fields are filled)

**Functionality**:
- On submit: Call `POST /api/auth/login`
- On success: Redirect to homepage (Movies page)
- On failure: Show generic error "Invalid credentials" (don't specify username/password)

#### 2. Media Library Pages (Movies & TV Shows)
**Layout**:
- View toggle buttons in top-right: Grid view / List view
- Grid view: Display media poster images with titles in card layout
  - Each card shows: Poster image, title, year, season/episode count (for TV shows)
  - Poster images fetched from `GET /api/media/{media_id}/poster`
  - Use placeholder image if `has_poster` is false or poster fails to load
- List view: Display media as table rows with key info (title, year, status, etc.)
- Pagination controls at bottom

**Functionality**:
- **Movies**: Fetch data from `GET /api/media/movies`
- **TV Shows**: Fetch data from `GET /api/media/tvshows/grouped` (shows grouped by title, one card per show)
- Only display media with existence_status = "exists"
- Check `has_poster` field to determine if poster is available
- Display poster using: `<img src="/api/media/{media_id}/poster" />`
- Click on item: Navigate to Media Detail page (same content area)

**Optimization**:
- Added search, filter, and pagination for better UX with large libraries
- TV shows grouped by title with season/episode counts for cleaner browsing

#### 3. Media Detail Page
**Layout**:
- Header section:
  - Poster image (left side, fetched from `GET /api/media/{media_id}/poster`)
  - Media title, metadata (type, year, overview, cast) on the right
- Content section below header

**For TV Shows**:
- Two-level hierarchy: Seasons (Level 1) → Episodes (Level 2)
- Each episode displays:
  - Episode number and title
  - Episode overview
  - Video filename
  - Generated subtitle filename (if exists)
  - Other subtitle files in the same directory (if any)
  - Processing status indicator

**For Movies**:
- Video filename
- Generated subtitle filename (if exists)
- Other subtitle files in the same directory (if any)
- Processing status indicator

**Functionality**:
- **Movies**: Fetch data from `GET /api/media/{media_id}` and `GET /api/media/{media_id}/files`
- **TV Shows**: Fetch hierarchical data from `GET /api/media/tvshows/detail/{show_title}` (seasons → episodes)
- Display task status if currently processing (poll `GET /api/tasks` with media filter)
- Provide manual trigger button for processing (calls `POST /api/tasks/trigger`)

**Optimization**: Added task status visibility and manual trigger option.

#### 4. Task List Page
**Layout**:
- Table view of tasks with columns: Media name, Status, Created time, Actions
- Filter options: Status (all/pending/processing/failed)
- Pagination controls

**Functionality**:
- Fetch from `GET /api/tasks` with filtering
- Action buttons per task:
  - Retry button (for failed tasks): Calls `POST /api/tasks/{task_id}/retry`
  - Cancel button (for pending/processing tasks): Calls `POST /api/tasks/{task_id}/cancel`
- Auto-refresh every 30 seconds via polling

**Optimization**: New dedicated page for task visibility and management.

#### 5. Processing History Page
**Layout**:
- Table view with columns: Media name, Status, Duration, Created time, Error details
- Search box for filtering by media name
- Success/failure statistics summary at top
- Pagination controls

**Functionality**:
- Fetch from `GET /api/history` and `GET /api/history/stats`
- Display error details in expandable rows for failed items

### Sidebar Menu Items
1. **Media Records**
   - Movies (sub-item)
   - TV Shows (sub-item)
2. **Task List**
3. **Processing History**

### Internationalization
- Vue i18n for multi-language support
- Supported languages: English (default), Chinese
- Language selector in top navigation bar
- All UI strings externalized to locale files: `en.json`, `zh.json`

### State Management
- Pinia for global state management
- Store modules:
  - Auth store (user session, login/logout)
  - Media store (current media list, filters)
  - Task store (task list, polling state)

**Note**: No WebSocket or real-time progress reporting for simplicity. Task status updates via periodic polling (30s interval).

