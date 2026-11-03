# Deployment short guide

Use Docker as the default deployment path. Keep Python only for local debugging and troubleshooting.

## Default Docker setup

```bash
cd ~/yt-auto-clipping
cp .env.example .env
# fill in real values

docker-compose -f docker-compose.yml up --build -d
```

Open:

- http://127.0.0.1:8001/
- http://127.0.0.1:8001/docs

Compose files:

- `docker-compose.yml`
- `opensource-clipping/docker-compose.yml`

## Runtime policy

Docker is the only supported way to serve the dashboard app in this project.

- Use Docker for the web app and local preview
- Use Python only for automation and clipping tasks such as `pipeline.py`
- Do not launch the dashboard via a direct host Python process

## Project structure

```text
yt-auto-clipping/
├── raw/
│   ├── source/<video-slug>/video_asli.mp4
│   ├── source/<video-slug>/video_asli_preview.mp4
│   ├── categories/<video-slug>/
│   └── seen_videos.json
├── outputs/
├── uploads/
├── custom_fonts/
├── opensource-clipping/
│   ├── clipping/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── requirements.txt
├── setup_linux_host.sh
├── client_secrets.json
├── pipeline.py
├── README.md
├── .env.example
└── .env
```

## Daily workflow

```bash
cd ~/yt-auto-clipping
bash daily_run.sh
```

Each source video and its clips are grouped by video slug. The daily profile requests at most three 60–90-second clips per source, and `raw/seen_videos.json` prevents duplicate YouTube downloads by niche.

## Shorts covers

Cloudflare Workers AI FLUX Schnell creates optional 9:16 background artwork from the clip context. Exact title text is overlaid locally. Set `THUMBNAIL_PROVIDER=cloudflare`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, and `THUMBNAIL_IMAGE_MODEL=@cf/black-forest-labs/flux-1-schnell` in `.env`. The free Workers AI allocation is 10,000 Neurons per day; failed or over-quota requests fall back to a video frame. No paid provider is used as a fallback.

## Content strategy summary

For your channel, the final recommendation remains:

- always keep subtitles on
- keep design minimal
- keep the message strong and emotional
- use one sharp idea per clip
- use vertical 9:16 with minimal clutter

This is the best path for high RPM and engagement.

## Important notes

- Docker is the required method for serving the dashboard app.
- Python remains useful for automation, the pipeline, and debugging the processing code.
- Keep `.env`, credentials, and generated media out of version control.
