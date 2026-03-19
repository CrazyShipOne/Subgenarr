-- Video Subtitle Generation System - Database Schema
-- SQLite Database Creation Script

-- =============================================================================
-- 1. MEDIA LIBRARY TABLE
-- =============================================================================
-- Stores discovered media metadata and current state
-- Independent catalog of all media items found in the library

CREATE TABLE IF NOT EXISTS media_library (
    -- Primary identifier
    media_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- External identifiers
    tmdb_id TEXT,
    imdb_id TEXT,

    -- Media classification
    media_type TEXT NOT NULL CHECK(media_type IN ('movie', 'tv')),

    -- Core metadata
    title TEXT NOT NULL,
    year INTEGER,
    overview TEXT,
    cast TEXT, -- JSON array stored as text

    -- TV show specific fields
    season INTEGER,
    episode INTEGER,
    episode_overview TEXT,

    -- File paths
    video_file_path TEXT NOT NULL,
    nfo_file_path TEXT NOT NULL,
    subtitle_file_path TEXT, -- Generated subtitle file
    poster_path TEXT, -- Poster/artwork image (poster.jpg, folder.jpg, etc.)
    directory_path TEXT NOT NULL,

    -- Embedded subtitle flag (set when target-language subtitle stream is detected in video)
    has_embedded_subtitle INTEGER NOT NULL DEFAULT 0,

    -- Status tracking
    existence_status TEXT NOT NULL DEFAULT 'exists' CHECK(existence_status IN ('exists', 'deleted')),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(nfo_file_path)
);

-- Indexes for media_library
CREATE INDEX IF NOT EXISTS idx_media_library_type ON media_library(media_type);
CREATE INDEX IF NOT EXISTS idx_media_library_tmdb ON media_library(tmdb_id);
CREATE INDEX IF NOT EXISTS idx_media_library_imdb ON media_library(imdb_id);
CREATE INDEX IF NOT EXISTS idx_media_library_status ON media_library(existence_status);
CREATE INDEX IF NOT EXISTS idx_media_library_directory ON media_library(directory_path);
CREATE INDEX IF NOT EXISTS idx_media_library_created ON media_library(created_at);
CREATE INDEX IF NOT EXISTS idx_media_library_video_path ON media_library(video_file_path);

-- =============================================================================
-- 2. TASK QUEUE TABLE
-- =============================================================================
-- Tracks items pending or in-progress processing
-- Active queue for coordinating worker processes

CREATE TABLE IF NOT EXISTS task_queue (
    -- Primary identifier
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Media reference
    media_id INTEGER NOT NULL,

    -- File paths (duplicated for quick access without joins)
    nfo_file_path TEXT NOT NULL,
    video_file_path TEXT NOT NULL,

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'metadata_fetching', 'processing', 'completed', 'failed')),

    -- Retry and error tracking
    retry_count INTEGER NOT NULL DEFAULT 0,
    failure_reason TEXT,

    -- Worker coordination
    worker_assignment TEXT,

    -- Timing information
    queued_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_time TIMESTAMP,
    timeout_deadline TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key
    FOREIGN KEY (media_id) REFERENCES media_library(media_id) ON DELETE CASCADE
);

-- Indexes for task_queue
CREATE INDEX IF NOT EXISTS idx_task_queue_media ON task_queue(media_id);
CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_worker ON task_queue(worker_assignment);
CREATE INDEX IF NOT EXISTS idx_task_queue_nfo_path ON task_queue(nfo_file_path);
CREATE INDEX IF NOT EXISTS idx_task_queue_created ON task_queue(created_at);
CREATE INDEX IF NOT EXISTS idx_task_queue_timeout ON task_queue(timeout_deadline);
CREATE INDEX IF NOT EXISTS idx_task_queue_retry ON task_queue(retry_count, status);

-- Composite index for task acquisition query
CREATE INDEX IF NOT EXISTS idx_task_queue_acquisition ON task_queue(status, retry_count, created_at);

-- =============================================================================
-- 3. PROCESSING HISTORY TABLE
-- =============================================================================
-- Immutable audit log of all processing attempts
-- Used for analytics, debugging, and historical tracking

CREATE TABLE IF NOT EXISTS processing_history (
    -- Primary identifier
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Task reference (may be NULL if task is deleted from queue)
    task_id INTEGER,

    -- Media reference
    media_id INTEGER NOT NULL,

    -- Processing result
    status TEXT NOT NULL CHECK(status IN ('success', 'failed')),

    -- Performance tracking
    processing_duration_seconds INTEGER,

    -- Error tracking
    failure_reason TEXT,
    error_details TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key
    FOREIGN KEY (media_id) REFERENCES media_library(media_id) ON DELETE CASCADE
);

-- Indexes for processing_history
CREATE INDEX IF NOT EXISTS idx_processing_history_media ON processing_history(media_id);
CREATE INDEX IF NOT EXISTS idx_processing_history_task ON processing_history(task_id);
CREATE INDEX IF NOT EXISTS idx_processing_history_status ON processing_history(status);
CREATE INDEX IF NOT EXISTS idx_processing_history_created ON processing_history(created_at);

-- Composite index for statistics queries
CREATE INDEX IF NOT EXISTS idx_processing_history_stats ON processing_history(status, created_at);

-- =============================================================================
-- 4. TRIGGERS
-- =============================================================================
-- Automatic timestamp updates

-- Trigger for media_library updated_at
CREATE TRIGGER IF NOT EXISTS trigger_media_library_updated
AFTER UPDATE ON media_library
FOR EACH ROW
BEGIN
    UPDATE media_library SET updated_at = CURRENT_TIMESTAMP WHERE media_id = NEW.media_id;
END;

-- Trigger for task_queue updated_at
CREATE TRIGGER IF NOT EXISTS trigger_task_queue_updated
AFTER UPDATE ON task_queue
FOR EACH ROW
BEGIN
    UPDATE task_queue SET updated_at = CURRENT_TIMESTAMP WHERE task_id = NEW.task_id;
END;

-- Trigger for processing_history updated_at
CREATE TRIGGER IF NOT EXISTS trigger_processing_history_updated
AFTER UPDATE ON processing_history
FOR EACH ROW
BEGIN
    UPDATE processing_history SET updated_at = CURRENT_TIMESTAMP WHERE history_id = NEW.history_id;
END;

-- =============================================================================
-- 5. VIEWS (Optional - for convenience queries)
-- =============================================================================

-- Active tasks with media information
CREATE VIEW IF NOT EXISTS view_active_tasks AS
SELECT
    tq.task_id,
    tq.status,
    tq.retry_count,
    tq.worker_assignment,
    tq.started_time,
    tq.timeout_deadline,
    ml.media_id,
    ml.media_type,
    ml.title,
    ml.season,
    ml.episode,
    tq.video_file_path,
    tq.created_at AS task_created_at
FROM task_queue tq
JOIN media_library ml ON tq.media_id = ml.media_id
WHERE tq.status IN ('pending', 'metadata_fetching', 'processing');

-- Recent processing history with media information
CREATE VIEW IF NOT EXISTS view_recent_history AS
SELECT
    ph.history_id,
    ph.status,
    ph.processing_duration_seconds,
    ph.failure_reason,
    ph.created_at AS processed_at,
    ml.media_id,
    ml.media_type,
    ml.title,
    ml.season,
    ml.episode,
    ml.subtitle_file_path
FROM processing_history ph
JOIN media_library ml ON ph.media_id = ml.media_id
ORDER BY ph.created_at DESC;

-- Media library with processing status
CREATE VIEW IF NOT EXISTS view_media_with_status AS
SELECT
    ml.*,
    CASE
        WHEN ml.subtitle_file_path IS NOT NULL THEN 'completed'
        WHEN ml.has_embedded_subtitle = 1 THEN 'embed_found'
        WHEN EXISTS (SELECT 1 FROM task_queue tq WHERE tq.media_id = ml.media_id AND tq.status IN ('processing', 'metadata_fetching')) THEN 'processing'
        WHEN EXISTS (SELECT 1 FROM task_queue tq WHERE tq.media_id = ml.media_id AND tq.status = 'pending') THEN 'pending'
        WHEN EXISTS (SELECT 1 FROM task_queue tq WHERE tq.media_id = ml.media_id AND tq.status = 'failed') THEN 'failed'
        ELSE 'unprocessed'
    END AS processing_status
FROM media_library ml
WHERE ml.existence_status = 'exists';

-- =============================================================================
-- 6. INITIAL DATA (Optional)
-- =============================================================================
-- Add any default configuration or seed data here if needed
-- Currently none required based on specification
