# YT Auto Clipping

<img width="1917" height="941" alt="image" src="https://github.com/user-attachments/assets/413a323f-473f-40da-a5bb-a7b374bff345" />

**Discover long-form YouTube content, turn it into short vertical clips, and organize the results in one workflow.**

This project combines an automated YouTube discovery and publishing pipeline with the [`opensource-clipping/`](./opensource-clipping/) rendering engine and a Docker-served media dashboard. It is designed to keep content coverage balanced across configured niches while avoiding repeat processing of previously recorded videos.

> **Publishing note:** the automation uploads generated clips to YouTube with public visibility. Review your OAuth credentials, channel, and publishing settings before running it.

## What it does

- Searches YouTube for Creative Commons candidates using the niche search terms configured in [`pipeline.py`](./pipeline.py).
- Balances coverage by processing only the niche or niches with the fewest recorded video IDs.
- Checks `raw/seen_videos.json` to avoid reusing IDs recorded under any niche.
- Runs the clipping engine to create up to three 60–90 second vertical clips per selected source, using YouTube subtitles when available and a CUDA-enabled Whisper fallback.
- Uploads generated MP4 clips to YouTube Shorts.
- Provides a Docker dashboard to review and organize media, edit social-platform copy, and track publishing states.
- Supports optional AI-generated 9:16 thumbnail backgrounds through Cloudflare Workers AI, with a video-frame fallback.

## How the workflow runs

```text
daily_run.sh
    ├── validates raw/seen_videos.json
    ├── removes unlisted folders from raw/source/
    └── runs pipeline.py
          ├── selects the least-filled niche(s)
          ├── searches configured queries for Creative Commons videos
          ├── skips IDs already recorded across niches
          ├── renders clips with opensource-clipping/
          ├── uploads generated clips to YouTube
          └── records discovered IDs in raw/seen_videos.json
```

The pipeline handles every niche currently tied for the lowest count, and processes at most one new candidate per selected niche per run. Ties follow the order in [`NICHES`](./pipeline.py). If a candidate ID is already recorded, the pipeline continues to the next query.

`daily_run.sh` removes direct subfolders under `raw/source/` whose IDs are absent from the seen-video file. It stops before pruning if that JSON is missing or invalid. This cleanup is specific to source folders; keep the seen-video list accurate.

## Quick start

### 1. Set up the host

On a supported Linux host:

```bash
cd ~/yt-auto-clipping
bash setup_linux_host.sh
```

The setup script installs project dependencies, prepares the Python environment and working directories, and configures the Docker dashboard. For details, see the [host setup guide](./docs/HOST_SETUP.md).

### 2. Configure credentials and assets

Create your local environment file from the example:

```bash
cp .env.example .env
```

Add the credentials required for the features you use. YouTube publishing also requires a valid `client_secrets.json` for Google OAuth. Required fonts and the face-tracking model are documented in the [host setup guide](./docs/HOST_SETUP.md).

For optional Cloudflare thumbnail backgrounds, configure:

```env
THUMBNAIL_PROVIDER=cloudflare
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=
THUMBNAIL_IMAGE_MODEL=@cf/black-forest-labs/flux-1-schnell
```

If image generation is unavailable or fails, the renderer can use a frame from the clip instead. Check Cloudflare's current pricing and limits before enabling the service.

### 3. Run the daily pipeline

```bash
cd ~/yt-auto-clipping
bash daily_run.sh
```

The script writes a timestamped log under `logs/`. To run the Python automation directly, activate the root virtual environment and run `pipeline.py`:

```bash
. venv/bin/activate
python pipeline.py
```

### 4. Open the dashboard

The supported way to serve the dashboard is Docker Compose:

```bash
docker-compose -f docker-compose.yml up --build -d
```

Open [http://127.0.0.1:8001/](http://127.0.0.1:8001/). The dashboard is intended to run in Docker, not as a direct host-side Python process. See the [deployment guide](./docs/DEPLOYMENT.md) for additional details.

## Project structure

| Path | Purpose |
| --- | --- |
| [`pipeline.py`](./pipeline.py) | Niche search, deduplication, clipping orchestration, and YouTube upload |
| [`daily_run.sh`](./daily_run.sh) | Logged daily entry point and stale source-folder cleanup |
| [`opensource-clipping/`](./opensource-clipping/) | Video clipping and rendering engine |
| `raw/source/` | Downloaded source videos, grouped by video ID |
| `raw/categories/` | Rendered clip assets and related metadata |
| `raw/seen_videos.json` | Per-niche list of recorded YouTube video IDs |
| `outputs/` | Local pipeline output and bookkeeping |
| `uploads/` | Local staging area |
| [`server.py`](./server.py), [`dashboard_index.html`](./dashboard_index.html) | Dashboard backend and interface |
| `docker-compose.yml` | Root dashboard service configuration |
| `docs/` | Setup, deployment, and publishing guidance |

## Configure niches and search terms

Niches and their search queries are currently defined in the `NICHES` mapping near the top of [`pipeline.py`](./pipeline.py). The names must correspond to the keys used in `raw/seen_videos.json`. Each run prioritizes the niche group with the fewest recorded IDs so coverage can catch up evenly.

## Privacy and Git

Keep local credentials, downloaded media, generated clips, logs, and virtual environments out of version control. The root [`.gitignore`](./.gitignore) excludes these local files and common video formats. Image files are not ignored globally, so required static image assets can still be tracked.

Before pushing, inspect the staged file list and confirm that it contains no credentials or private media. Ignore rules do not remove files that were already added to Git.

## Troubleshooting

- **Dashboard unavailable:** confirm Docker is running and port `8001` is available. The dashboard should be served through Docker Compose.
- **OAuth or upload errors:** verify `client_secrets.json`, Google API configuration, requested YouTube upload permissions, and the account selected during authorization.
- **Source cleanup stops:** validate that `raw/seen_videos.json` is valid JSON containing a mapping of niche names to lists of 11-character YouTube IDs.
- **Whisper/PyAV compatibility:** a compatibility shim is maintained in `opensource-clipping/clipping/engine.py` for older `faster-whisper` calls with newer PyAV versions.

For further deployment details, see [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) and [`docs/PRODUCTION_DEPLOYMENT.md`](./docs/PRODUCTION_DEPLOYMENT.md).
