# Poster Image Support

The system now supports displaying poster/artwork images for movies and TV shows on the frontend.

## Overview

Poster images are automatically discovered during media scanning and served through the API. The frontend can display these images in grid view and detail pages.

## How It Works

### 1. Media Scanner (Worker Service)

The media scanner automatically searches for poster images following Jellyfin/Emby naming conventions:

**For Movies:**
- `poster.jpg` (most common)
- `movie.jpg`
- `folder.jpg`
- `{movie_name}-poster.jpg`
- Same filename as video

**For TV Show Episodes:**
- `season{XX}-poster.jpg` (e.g., `season01-poster.jpg`)
- `season{X}-poster.jpg` (e.g., `season1-poster.jpg`)
- `poster.jpg` (show poster)
- `folder.jpg`
- Falls back to parent directory for show poster

**Supported formats:** `.jpg`, `.jpeg`, `.png`

### 2. Database Storage

Poster paths are stored in the `media_library` table:

```sql
poster_path VARCHAR(1000) NULL
```

The path points to the full filesystem path of the poster image.

### 3. API Endpoints

#### Get Poster Image
```http
GET /api/media/{media_id}/poster
```

**Response:**
- Returns the image file with proper Content-Type (`image/jpeg`, `image/png`)
- Includes caching headers (`Cache-Control`, `ETag`)
- Returns 404 if poster not found

**Features:**
- No authentication required (public images)
- Browser caching for 24 hours
- ETag-based cache validation

#### Media List/Detail Endpoints

All media endpoints now include a `has_poster` boolean field:

```json
{
  "media_id": 123,
  "title": "Movie Title",
  "has_poster": true,
  ...
}
```

## Frontend Usage

### Display Poster in Grid View

```vue
<template>
  <div class="movie-card">
    <img
      v-if="media.has_poster"
      :src="`/api/media/${media.media_id}/poster`"
      :alt="media.title"
      @error="handleImageError"
    />
    <div v-else class="placeholder-image">
      No Poster
    </div>
    <h3>{{ media.title }}</h3>
  </div>
</template>

<script>
export default {
  methods: {
    handleImageError(event) {
      // Fallback to placeholder if image fails to load
      event.target.style.display = 'none';
    }
  }
}
</script>
```

### Display Poster in Detail Page

```vue
<template>
  <div class="media-detail">
    <img
      v-if="media.has_poster"
      :src="`/api/media/${media.media_id}/poster`"
      :alt="media.title"
      class="detail-poster"
    />
    <div class="media-info">
      <h1>{{ media.title }}</h1>
      <!-- other details -->
    </div>
  </div>
</template>
```

## Database Migration

For existing databases, run the migration script:

```bash
cd backend_service/shared
python migrate_add_poster.py
```

This adds the `poster_path` column to the `media_library` table.

**Note:** Existing media entries will have `NULL` poster paths. Re-run the media scanner to populate them:
- The scanner will automatically find and update poster paths on the next scan cycle
- Or restart the worker service to trigger an immediate scan

## File Structure Example

### Movie Directory
```
/media/movies/The Matrix (1999)/
├── The Matrix (1999).mkv          # Video file
├── movie.nfo                       # NFO metadata
├── poster.jpg                      # ← Poster image (auto-detected)
└── The Matrix (1999)_en_0.srt     # Subtitle
```

### TV Show Directory
```
/media/tv/Breaking Bad/
├── poster.jpg                      # Show poster (fallback)
└── Season 01/
    ├── Breaking Bad - S01E01.mkv
    ├── Breaking Bad - S01E01.nfo
    ├── season01-poster.jpg         # ← Season poster (preferred)
    └── Breaking Bad - S01E01_en_0.srt
```

## Caching

The API uses HTTP caching for optimal performance:

**Cache-Control:** `public, max-age=86400` (24 hours)
- Browsers cache poster images for 24 hours
- Reduces server load and improves page load times

**ETag:** Based on media_id and file modification time
- Enables conditional requests (304 Not Modified)
- Automatically updates when poster file changes

## Troubleshooting

### Poster not showing on frontend

1. **Check if poster path is stored:**
   ```sql
   SELECT media_id, title, poster_path FROM media_library WHERE media_id = 123;
   ```

2. **Verify file exists:**
   ```bash
   ls -la /path/to/poster.jpg
   ```

3. **Check API endpoint:**
   ```bash
   curl http://localhost:8000/api/media/123/poster -I
   ```

4. **Re-scan media directory:**
   - Restart worker service
   - Wait for next scheduled scan (default: 1 hour)
   - Scanner will find and update poster paths

### Missing posters after migration

Run media scanner to populate poster paths:
- Restart worker service for immediate scan
- Or wait for scheduled scan cycle (1 hour default)

### Poster image format issues

Supported formats: `.jpg`, `.jpeg`, `.png`

If using other formats, convert to JPEG:
```bash
convert poster.webp poster.jpg
```

## Performance Considerations

- **Caching:** 24-hour browser cache reduces API calls
- **No Database Query:** Poster endpoint reads directly from filesystem
- **Lazy Loading:** Frontend should implement lazy loading for better performance:

```vue
<img
  :src="`/api/media/${media.media_id}/poster`"
  loading="lazy"
  :alt="media.title"
/>
```

## Security

- **No Path Traversal:** Poster paths are validated against database entries
- **Public Access:** Poster endpoint doesn't require authentication
  - Safe: Only serves images explicitly registered in database
  - Cannot access arbitrary filesystem locations
- **File Type Validation:** Only serves JPEG/PNG files
