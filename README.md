# YT Auto Clipping

This is the working directory for the automation workflow and the clipping engine. It includes the root automation files, the dashboard, and the cloned upstream clipping repo so you can start from scratch from one place.

## Project layout

- `pipeline.py` — local automation entry point for discovery + upload workflow
- `setup_linux_host.sh` — full Linux setup and dependency install
- `opensource-clipping/` — upstream clipping engine used for rendering clips
- `raw/` — raw media storage for the working project
  - `raw/source/<video-slug>/video_asli.mp4` — source video kept with its run
  - `raw/categories/<video-slug>/` — clips, covers, metadata, and render manifest for that source
  - `raw/seen_videos.json` — per-niche dedupe cache to skip already processed YouTube IDs
- `outputs/` — processed files and upload bookkeeping
- `uploads/` — incoming media and staging area
- `custom_fonts/` — typography assets for rendering
- `docs/` — setup and deployment notes for this working directory
- `dashboard_index.html` and `server.py` — Docker-served publishing library with editable YouTube, TikTok, and Instagram copy and upload states

## Start from scratch

```bash
cd ~/yt-auto-clipping
bash setup_linux_host.sh
```

This will:

- install base host dependencies
- install Node/Docker tooling
- clone or refresh `opensource-clipping`
- create a Python virtual environment at `venv/`
- install the clipping dependencies
- start the dashboard on http://127.0.0.1:8001/

## Run the pipeline daily

Use the project script for a repeatable daily run. For each source video, it requests at most three high-scoring clips between 60 and 90 seconds, uses YouTube subtitles when word-level timing is available (otherwise falling back to GPU Whisper), and disables B-roll to reduce processing time.

```bash
cd ~/yt-auto-clipping
bash daily_run.sh
```

You can also run it directly if you want the raw Python path:

```bash
cd ~/yt-auto-clipping
. venv/bin/activate
python pipeline.py
```

This workflow counts recorded IDs for all configured niches in `raw/seen_videos.json` and processes only niches tied for the lowest count, adding at most one new video ID per selected niche per run. This lets underrepresented niches catch up without advancing already-ahead niches. If counts are tied, their configured order is preserved. It skips any video ID already recorded there across all niches and tries the next search query when a result has already been processed.

Before starting the pipeline, `daily_run.sh` removes direct subfolders of `raw/source/` whose video IDs are not present in `raw/seen_videos.json`. If the JSON is missing or invalid, the run stops without pruning.

This workflow is designed to:

- scan each niche from `NICHES` in `pipeline.py`
- skip duplicate YouTube video IDs already saved in `raw/seen_videos.json`
- download a fresh source video only when a new niche candidate is found
- keep the active source media under `raw/source/`
- keep each source and its related clips grouped by video ID under `raw/source/<video-slug>/` and `raw/categories/<video-slug>/`
- generate no more than 3 clips from each source video, each 60–90 seconds long

Open the Docker dashboard at http://127.0.0.1:8001/ to review covers and clips, edit platform titles/descriptions/tags/captions, and track draft, ready, scheduled, uploaded, or failed states. Saved settings are also written into each render manifest for uploader compatibility.

## Shorts thumbnails

Thumbnail backgrounds use Cloudflare Workers AI FLUX Schnell when `THUMBNAIL_PROVIDER=cloudflare` is configured. The model generates a 9:16 concept image; the exact title text is added locally, and the final JPEG is saved with the clip as `thumbnail_rank_N.jpg`. The current free Workers AI plan includes 10,000 Neurons per day. If generation fails or the free quota is exhausted, the renderer uses a frame from the clip instead. It does not switch to a paid provider.

Configure these values in `.env`:

```env
THUMBNAIL_PROVIDER=cloudflare
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=
THUMBNAIL_IMAGE_MODEL=@cf/black-forest-labs/flux-1-schnell
```

Keep the account token private. To avoid charges, stay on the Workers Free plan; requests past the free quota should fail and use the local frame fallback.

## Known compatibility fix

The upstream `opensource-clipping` repo relies on `faster-whisper`, which still calls `av.open(..., metadata_errors="ignore")` in older code paths. Newer PyAV versions removed that keyword, so the runtime shim in `opensource-clipping/clipping/engine.py` strips the unsupported argument before the call. This prevents the `TypeError: open() got an unexpected keyword argument 'metadata_errors'` crash.

## Run the dashboard

```bash
cd ~/yt-auto-clipping
docker-compose -f docker-compose.yml up --build -d
```

Then open:

- http://127.0.0.1:8001/

The dashboard is served through Docker only; do not start it directly with a host-side Python command.

## Channel strategy for high RPM and engagement

For this channel, the recommended creative standard is:

- always keep subtitles on
- keep the design minimal
- keep the message strong and emotional
- use one sharp idea per clip
- use vertical 9:16 with minimal clutter

This is the best path for high RPM and engagement.

## Content workflow

For each clip:

1. choose one strong idea
2. keep the subtitle text tight and readable
3. keep the visual background clean
4. prioritize emotion, tension, and clarity over complexity
5. make sure the clip feels instantly understandable in the first 1-2 seconds

## Next-step production options

For any generated clip, you can now do the following:

- generate the best title + thumbnail text
- generate the exact short-form caption for posting
- create a second variation with a more aggressive subtitle style

## Important notes

- The automation entry point lives at the root of this project.
- The clipping engine remains in `opensource-clipping/` and is treated as the processing dependency.
- Keep secrets like `.env`, `client_secrets.json`, and generated media inside this working directory only.
- The recommended long-term workflow is: generate clip → review hook + subtitle clarity → export thumbnail/title/caption → publish short-form version.
