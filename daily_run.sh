#!/usr/bin/env bash
# Stop on errors, unset variables, and failed commands in pipelines.
set -euo pipefail

# Resolve the project root from this script's location.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Set up the directory and timestamped file used for this run's logs.
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"
DATE_TAG="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/daily_run_${DATE_TAG}.log"

# Show Python output immediately and add timestamps to shell trace messages.
export PYTHONUNBUFFERED=1
export PS4='+ $(date -u +"%Y-%m-%d %H:%M:%S UTC") [$$] '

# Send both output streams to the terminal and append them to the run log.
exec > >(tee -a "$LOG_FILE") 2> >(tee -a "$LOG_FILE" >&2)

# Trace subsequent shell commands for troubleshooting.
set -x

# Run all project-relative commands from the project root.
cd "$ROOT_DIR"

# Require the project's virtual environment before starting.
if [ ! -d "$ROOT_DIR/venv" ]; then
  echo "[daily_run] Missing venv at $ROOT_DIR/venv" >&2
  exit 1
fi

# Activate the virtual environment used by the pipeline.
# shellcheck disable=SC1091
. "$ROOT_DIR/venv/bin/activate"

# Record the pipeline start time in UTC.
echo "[daily_run] Starting daily pipeline at $(date -u +'%Y-%m-%d %H:%M:%S UTC')"

# Remove source folders whose IDs are absent from the seen-video list.
python - "$ROOT_DIR" <<'PY'
import json
import re
import shutil
import sys
from pathlib import Path

# Resolve the paths to the deduplication data and downloaded source videos.
root_dir = Path(sys.argv[1])
seen_path = root_dir / "raw" / "seen_videos.json"
source_dir = root_dir / "raw" / "source"

# Read and parse the seen-video list; stop rather than delete on read errors.
try:
    seen_data = json.loads(seen_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"[daily_run] Cannot safely prune source folders: {exc}")

# Require an object at the top level so malformed data cannot trigger pruning.
if not isinstance(seen_data, dict):
    raise SystemExit("[daily_run] Cannot safely prune source folders: seen_videos.json must contain an object")

# Validate every niche's ID list and collect all IDs across niches.
seen_ids = set()
for niche, video_ids in seen_data.items():
    if not isinstance(video_ids, list) or any(
        not isinstance(video_id, str)
        or re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id) is None
        for video_id in video_ids
    ):
        raise SystemExit(
            f"[daily_run] Cannot safely prune source folders: invalid video ID list for {niche!r}"
        )
    seen_ids.update(video_ids)

# Refuse to traverse a symlink, which could point cleanup outside the project.
if source_dir.is_symlink():
    raise SystemExit("[daily_run] Cannot safely prune source folders: raw/source must not be a symlink")

# Inspect only direct child directories and remove folders without a listed ID.
if source_dir.exists():
    for folder in source_dir.iterdir():
        # Preserve symlinks and non-directory entries.
        if folder.is_symlink() or not folder.is_dir():
            continue
        # Source folder names use the video_1_<11-character YouTube ID format.
        match = re.fullmatch(r"video_1_([A-Za-z0-9_-]{11})", folder.name)
        if match is None or match.group(1) not in seen_ids:
            print(f"[daily_run] Removing source folder not listed in seen_videos.json: {folder}")
            shutil.rmtree(folder)
PY

# Run the daily clipping and publishing pipeline.
python -u pipeline.py

# Record successful completion time in UTC.
echo "[daily_run] Completed successfully at $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
