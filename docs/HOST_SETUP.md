# Host setup quickstart

Use this if you want to install the project on a fresh Ubuntu host.

## 1) Run the installer

```bash
cd ~/yt-auto-clipping
bash setup_linux_host.sh
```

The installer does the following:

- installs the required apt packages
- installs Docker if missing
- creates the Python venv in the root project
- installs `opensource-clipping/requirements.txt`
- clones the upstream repo if it is missing
- ensures the canonical working directories exist:
  - `raw/source/`
  - `raw/categories/`
  - `raw/seen_videos.json`
- stores each new source and its related clips in matching video-slug folders
- keeps the clipping engine under `opensource-clipping/`
- starts the app through the root Docker Compose file by default

## Daily run and dedupe

Use this command every day. Each source is limited to 3 clips of 60–90 seconds; the run tries YouTube captions first, then uses the faster CUDA-enabled tiny Whisper model when word-level caption timing is unavailable, and skips B-roll for faster rendering. The tiny model is faster but less accurate than larger Whisper models.

```bash
cd ~/yt-auto-clipping
bash daily_run.sh
```

The automation now stores seen YouTube IDs in `raw/seen_videos.json` and skips them by niche, so the same video is not downloaded again and again.

## PyAV + Whisper compatibility

If you hit the following error:

```text
TypeError: open() got an unexpected keyword argument 'metadata_errors'
```

this is caused by a newer PyAV version being incompatible with the older `faster-whisper` call pattern. The runtime fix is already present in `opensource-clipping/clipping/engine.py` and should be preserved for future setups.

## 2) Docker is the required path

Compose file:

- `docker-compose.yml`

Open the app at:

- http://127.0.0.1:8001/

The dashboard is expected to run inside Docker only. Do not start it directly with Python on the host.
It groups source videos with their clips and lets you edit platform copy and track each platform's upload state.

## 3) Required files

Before processing content, confirm these exist:

- `client_secrets.json`
- `custom_fonts/Montserrat-Black.ttf`
- `custom_fonts/Montserrat-Regular.ttf`
- `custom_fonts/Anton-Regular.ttf`
- `blaze_face_full_range.tflite`
- `.env`

## 4) Env values

```bash
cd ~/yt-auto-clipping
cp .env.example .env
```

At minimum, set:

```env
GOOGLE_API_KEY=
PEXELS_API_KEY=
HF_TOKEN=
NVIDIA_API_KEY=
```

For generated Shorts cover backgrounds, configure the Cloudflare Workers AI free tier:

```env
THUMBNAIL_PROVIDER=cloudflare
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=
THUMBNAIL_IMAGE_MODEL=@cf/black-forest-labs/flux-1-schnell
```

Generated cover text is composited locally. If Cloudflare is not configured or generation fails, the thumbnail uses a frame from the clip. Workers AI currently includes a 10,000-Neuron daily free allocation; do not upgrade to a paid Workers plan if you want to avoid charges.

## 5) Channel content rules

For this channel, keep these rules consistent for every clip:

- always keep subtitles on
- keep the design minimal
- keep the message strong and emotional
- use one sharp idea per clip
- use vertical 9:16 with minimal clutter

This is the best path for high RPM and engagement.

## 6) Troubleshooting

- Docker daemon not running: `sudo systemctl enable --now docker`
- Old container still running: `docker-compose down` or `docker-compose rm -f`
- Port already in use: stop the old listener or edit the compose port mapping

For the full workflow, see `README.md`.
