// Common response types
export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export interface PaginationInfo {
  page: number
  page_size: number
  total_items: number
  total_pages: number
}

// Media types
export interface MediaItem {
  media_id: number
  media_type: 'movie' | 'tv'
  title: string
  year: number | null
  overview: string | null
  tmdb_id: string | null
  imdb_id: string | null
  cast: string[] | null
  season?: number | null
  episode?: number | null
  episode_overview?: string | null
  video_file_path: string
  subtitle_file_path: string | null
  has_poster: boolean
  directory_path: string
  existence_status: string
  processing_status: string
  created_at: string
  updated_at: string
}

export interface TVShowGrouped {
  media_id: number
  media_type: 'tv'
  title: string
  year: number | null
  overview: string | null
  tmdb_id: string | null
  imdb_id: string | null
  cast: string[] | null
  season_count: number
  episode_count: number
  has_poster: boolean
  created_at: string
  updated_at: string
}

export interface TVShowEpisode {
  media_id: number
  episode_number: number | null
  episode_overview: string | null
  video_file_path: string
  subtitle_file_path: string | null
  has_poster: boolean
  processing_status: string
  created_at: string
  updated_at: string
}

export interface TVShowSeason {
  season_number: number
  episodes: TVShowEpisode[]
}

export interface TVShowDetail {
  title: string
  media_type: 'tv'
  year: number | null
  overview: string | null
  tmdb_id: string | null
  imdb_id: string | null
  cast: string[] | null
  has_poster: boolean
  season_count: number
  episode_count: number
  seasons: TVShowSeason[]
}

export interface MediaDetail {
  media_id: number
  media_type: 'movie' | 'tv'
  title: string
  year: number | null
  overview: string | null
  tmdb_id: string | null
  imdb_id: string | null
  cast: string[] | null
  season: number | null
  episode: number | null
  episode_overview: string | null
  video_file_path: string
  nfo_file_path: string
  subtitle_file_path: string | null
  has_poster: boolean
  directory_path: string
  existence_status: string
  processing_status: string
  created_at: string
  updated_at: string
}

export interface FileInfo {
  path: string
  size_bytes: number
  language?: string
  exists: boolean
}

export interface MediaFiles {
  media_id: number
  directory_path: string
  files: {
    video?: FileInfo
    nfo?: FileInfo
    generated_subtitle?: FileInfo
    other_subtitles: FileInfo[]
  }
}

// Task types
export interface Task {
  task_id: number
  media_id: number
  media_title: string
  media_type: 'movie' | 'tv'
  season: number | null
  episode: number | null
  status: string
  retry_count: number
  failure_reason: string | null
  worker_assignment: string | null
  queued_time: string
  started_time: string | null
  timeout_deadline: string | null
  created_at: string
  updated_at: string
}

// History types
export interface HistoryItem {
  history_id: number
  task_id: number | null
  media_id: number
  media_title: string
  media_type: 'movie' | 'tv'
  season: number | null
  episode: number | null
  status: 'success' | 'failed'
  processing_duration_seconds: number | null
  failure_reason: string | null
  error_details: string | null
  created_at: string
}

export interface HistoryStats {
  total_processed: number
  successful: number
  failed: number
  success_rate: number
  average_duration_seconds: number
  total_duration_seconds: number
  failure_reasons: Record<string, number>
  processing_by_date: Array<{
    date: string
    total: number
    successful: number
    failed: number
  }>
}

// Auth types
export interface LoginRequest {
  username: string
  password: string
}

export interface User {
  username: string
}
