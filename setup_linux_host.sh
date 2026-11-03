#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_PREFIX="[yt-auto-clipping]"

echo "$LOG_PREFIX Starting fresh setup for yt-auto-clipping"

if ! command -v sudo >/dev/null 2>&1; then
  echo "$LOG_PREFIX sudo is required. Install sudo and rerun this script."
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "$LOG_PREFIX Unsupported OS. This installer targets Ubuntu/Debian-based Linux systems."
  exit 1
fi

# 1) Install base tools
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git \
  curl \
  ffmpeg \
  python3-pip \
  python3-venv \
  build-essential \
  ca-certificates \
  gnupg \
  libgl1 \
  libglib2.0-0 \
  libsm6 \
  libxext6 \
  libxrender1

# 2) Ensure Node 20+ is installed for the Vite dashboard
if ! command -v node >/dev/null 2>&1 || ! node -v | grep -qE '^v20|^v22'; then
  echo "$LOG_PREFIX Installing Node.js 20.x"
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

# 3) Ensure Docker is available
if ! command -v docker >/dev/null 2>&1; then
  echo "$LOG_PREFIX Docker not found. Installing Docker..."
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

if ! docker info >/dev/null 2>&1; then
  echo "$LOG_PREFIX Starting Docker daemon..."
  sudo systemctl enable --now docker
fi

if ! id -nG "$USER" | grep -qw docker; then
  echo "$LOG_PREFIX Adding $USER to the docker group. Log out and back in before Docker works correctly."
  sudo usermod -aG docker "$USER"
  echo "$LOG_PREFIX Docker group updated. Please log out and log back in, then rerun this script."
  exit 0
fi

# 4) Create the project folders
for dir in raw raw/source raw/categories outputs uploads custom_fonts web/dashboard; do
  mkdir -p "$ROOT_DIR/$dir"
done

# Ensure the daily dedupe cache file exists with the project default layout.
if [ ! -f "$ROOT_DIR/raw/seen_videos.json" ]; then
  echo '{ }' > "$ROOT_DIR/raw/seen_videos.json"
fi

# 5) Clone the upstream clipping project used for media processing
if [ ! -d "$ROOT_DIR/opensource-clipping/.git" ]; then
  echo "$LOG_PREFIX Cloning opensource-clipping into $ROOT_DIR/opensource-clipping"
  git clone https://github.com/NaufalRizqullah/opensource-clipping "$ROOT_DIR/opensource-clipping"
else
  echo "$LOG_PREFIX opensource-clipping already present; refreshing the repo"
  git -C "$ROOT_DIR/opensource-clipping" pull --ff-only || true
fi

# 6) Prepare Python environment for the clipping project
CLIPPING_DIR="$ROOT_DIR/opensource-clipping"
ROOT_VENV_DIR="$ROOT_DIR/venv"
CLIP_VENV_DIR="$CLIPPING_DIR/.venv"

if [ ! -d "$ROOT_VENV_DIR" ]; then
  echo "$LOG_PREFIX Creating root Python virtual environment for automation"
  python3 -m venv "$ROOT_VENV_DIR"
fi

if [ ! -d "$CLIP_VENV_DIR" ]; then
  echo "$LOG_PREFIX Creating project Python virtual environment for opensource-clipping"
  python3 -m venv "$CLIP_VENV_DIR"
fi

"$ROOT_VENV_DIR/bin/python" -m pip install --upgrade pip
if [ -f "$CLIPPING_DIR/requirements.txt" ]; then
  echo "$LOG_PREFIX Installing Python dependencies for opensource-clipping into the repo venv"
  "$CLIP_VENV_DIR/bin/pip" install -r "$CLIPPING_DIR/requirements.txt"
fi
if [ -f "$CLIPPING_DIR/pyproject.toml" ]; then
  echo "$LOG_PREFIX Installing opensource-clipping in editable mode"
  "$CLIP_VENV_DIR/bin/pip" install -e "$CLIPPING_DIR"
fi
if [ -f "$ROOT_VENV_DIR/bin/python" ] && [ -f "$CLIPPING_DIR/requirements.txt" ]; then
  echo "$LOG_PREFIX Installing the same requirements into the root automation venv for pipeline compatibility"
  "$ROOT_VENV_DIR/bin/pip" install -r "$CLIPPING_DIR/requirements.txt"
fi
if [ ! -f "$CLIPPING_DIR/.env" ] && [ -f "$CLIPPING_DIR/.env.sample" ]; then
  echo "$LOG_PREFIX Copying sample .env file into opensource-clipping"
  cp "$CLIPPING_DIR/.env.sample" "$CLIPPING_DIR/.env"
fi

# 7) Install and build the dashboard app
if [ -f "$ROOT_DIR/web/dashboard/package.json" ]; then
  echo "$LOG_PREFIX Installing dashboard dependencies"
  cd "$ROOT_DIR/web/dashboard"
  npm install
  npm run build
fi

# 8) Start the dashboard container if compose exists
if [ -f "$ROOT_DIR/docker-compose.yml" ]; then
  echo "$LOG_PREFIX Starting dashboard via Docker"
  if docker compose version >/dev/null 2>&1; then
    docker compose -f "$ROOT_DIR/docker-compose.yml" up --build -d
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f "$ROOT_DIR/docker-compose.yml" up --build -d
  else
    echo "$LOG_PREFIX Docker Compose is not available after install."
    exit 1
  fi
fi

echo "$LOG_PREFIX Setup complete."
echo "$LOG_PREFIX Dashboard: http://127.0.0.1:8001/"
echo "$LOG_PREFIX Automation working directory: $ROOT_DIR"
echo "$LOG_PREFIX Clipping working directory: $CLIPPING_DIR"
echo "$LOG_PREFIX To start clipping: cd $ROOT_DIR && . venv/bin/activate && python pipeline.py"
