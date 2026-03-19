# Subgenarr

Automated subtitle generation for movies and TV shows using multimodal AI (audio + video frames). Designed to work alongside Jellyfin/Emby media libraries.

## Features

- **Automatic Media Discovery** — Scans media directories for movies and TV shows using NFO metadata files
- **AI Subtitle Generation** — Uses multimodal LLM (audio + screenshots) for accurate transcription
- **Web Interface** — Browse media, monitor tasks, and view processing history
- **Task Management** — Queue, retry, and cancel subtitle generation jobs
- **Multilingual UI** — English and Chinese interface

## Requirements

- Docker & Docker Compose
- Media library with NFO files (Jellyfin/Emby format)
- OpenAI-compatible LLM API with **vision support** (OpenAI, Azure, Ollama, vLLM, etc.)
- [TMDb API key](https://www.themoviedb.org/settings/api)
- [OMDb API key](http://www.omdbapi.com/apikey.aspx)

## Quick Start

### 1. Download and Configure

```bash
curl -O https://raw.githubusercontent.com/crazyship/subgenarr/main/docker-compose.yml
curl -O https://raw.githubusercontent.com/crazyship/subgenarr/main/.env.example
cp .env.example .env
# Edit .env with your settings
```

### 2. Prepare Media Directory

NFO files are required for media discovery. Jellyfin and Emby generate these automatically.

```
media/
├── movies/
│   └── The Matrix (1999)/
│       ├── The Matrix (1999).mkv
│       ├── movie.nfo
│       └── poster.jpg
└── tv/
    └── Breaking Bad/
        ├── poster.jpg
        └── Season 01/
            ├── Breaking Bad - S01E01.mkv
            ├── Breaking Bad - S01E01.nfo
            └── poster.jpg
```

### 3. Start

```bash
docker-compose up -d
```

Open http://localhost:3500 and log in with the credentials set in `.env`.

### Build from Source

To build images locally instead of using Docker Hub:

```bash
git clone <repository-url>
cd subgenarr
cp .env.example .env
docker-compose -f docker-compose.build.yml up -d
```

Media scanning starts automatically on launch and repeats every hour. Subtitle generation can be triggered manually from the media detail page, or will run automatically when new files are detected.

Generated subtitle files are saved alongside the video file in Jellyfin/Emby-compatible format:
```
Breaking Bad - S01E01.en.srt
```

---

## Configuration

All settings are configured via `.env`. See `.env.example` for the full list.

### AI

| Variable | Description | Default |
|---|---|---|
| `AI_BASE_URL` | LLM API endpoint | `http://localhost:11434/v1` |
| `AI_API_KEY` | API key | `ollama` |
| `AI_MODEL` | Model name (must support vision) | `gpt-4o` |
| `AI_TIMEOUT` | Request timeout in seconds | `300` |

```bash
# OpenAI
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-...
AI_MODEL=gpt-4o

# Ollama (local)
AI_BASE_URL=http://host.docker.internal:11434/v1
AI_API_KEY=ollama
AI_MODEL=llava
```

### Authentication

| Variable | Default |
|---|---|
| `AUTH_USERNAME` | `admin` |
| `AUTH_PASSWORD` | `admin123` |
| `SESSION_SECRET` | *(must change in production)* |

### Metadata

| Variable | Description |
|---|---|
| `TMDB_API_KEY` | TMDb API key for movie/show metadata |
| `OMDB_API_KEY` | OMDb API key |

### Processing

| Variable | Description | Default |
|---|---|---|
| `TARGET_SUBTITLE_LANGUAGE` | Output language code | `en` |
| `MAX_CONCURRENT_WORKERS` | Parallel processing tasks | `2` |
| `AUDIO_SEGMENT_DURATION` | Audio chunk size in seconds | `300` |
| `SCREENSHOTS_PER_SEGMENT` | Screenshots per audio segment | `10` |
| `TASK_TIMEOUT` | Max processing time per task (seconds) | `7200` |
| `SCAN_INTERVAL` | Media scan interval in seconds | `3600` |

### Volume Mounts

Configure paths in `docker-compose.yml`:

| Container Path | Description |
|---|---|
| `/media` | Media library (mounted read-only for the API) |
| `/config` | Database storage |
| `/tmp` | Temporary processing files |

### Ports

| Service | Default |
|---|---|
| Web UI | `3500` |
| API | `8000` |

---

## Troubleshooting

**Media not appearing**
- Confirm NFO files are present and valid XML
- Check worker logs: `docker logs subgenarr-worker`

**Subtitle generation failing**
- Verify AI API credentials and that the model supports vision input
- Ensure sufficient disk space in the tmp volume
- Check worker logs: `docker logs subgenarr-worker`

**Poster images not loading**
- Verify poster files exist in the media directory (`poster.jpg` or `folder.jpg`)

---

## License

Subgenarr is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

You are free to use, modify, and distribute this software under the terms of the GPL v3. Any derivative works must also be distributed under the same license.
