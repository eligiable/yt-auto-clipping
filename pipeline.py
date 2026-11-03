import os
import socket
import sys
import subprocess
import json
from pathlib import Path
import yt_dlp
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Map each content niche to the YouTube searches used to find candidate videos.
NICHES = {
    "Business & Entrepreneurship": ["Business podcasts", "Entrepreneur interviews"],
    "Motivation & Self-Improvement": ["Motivational podcast", "Discipline mindset"],
    "Wealth & Personal Finance": ["Millionaire interviews", "Money mindset podcast"],
    "Psychology & Human Behaviour": ["Psychology podcast", "Human behaviour explained"],
    "Relationships & Dating": ["Relationship podcast", "Dating advice interviews"],
    "Health & Fitness": ["Fitness podcast", "Health expert interviews"],
    "Technology & AI": ["AI podcast", "Tech founder interviews"],
    "Celebrity & Entertainment": ["Celebrity podcast interviews", "Actor interviews"],
    "Sports & Athlete Mindset": ["Athlete interviews", "Sports podcast highlights"],
    "Luxury & Lifestyle": ["Luxury lifestyle podcast", "Billionaire lifestyle"]
}

# Resolve project files and runtime locations relative to this script.
PROJECT_ROOT = Path(__file__).resolve().parent
CLIP_REPO_DIR = PROJECT_ROOT / "opensource-clipping"
REPO_VENV_PYTHON = CLIP_REPO_DIR / ".venv" / "bin" / "python"
ROOT_VENV_PYTHON = PROJECT_ROOT / "venv" / "bin" / "python"
SEEN_VIDEOS_PATH = PROJECT_ROOT / "raw" / "seen_videos.json"
# Request permission to publish videos to the authenticated YouTube channel.
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = PROJECT_ROOT / "client_secrets.json"


def extract_video_id(url):
    """Extract a YouTube video ID from a URL if present."""
    if not url:
        return None
    import re
    # Accept standard watch, short-link, and Shorts URL formats.
    match = re.search(r'(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})', url)
    if match:
        return match.group(1)
    return None


def load_seen_videos():
    """Load a per-niche seen-video map from disk."""
    # Ensure the parent directory exists before attempting to read the cache.
    SEEN_VIDEOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SEEN_VIDEOS_PATH.exists():
        return {niche: set() for niche in NICHES.keys()}

    try:
        data = json.loads(SEEN_VIDEOS_PATH.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {niche: set() for niche in NICHES.keys()}

    result = {niche: set() for niche in NICHES.keys()}
    if isinstance(data, dict):
        # Convert saved ID lists to sets for efficient membership checks.
        for niche, ids in data.items():
            if isinstance(ids, list):
                result[niche] = set(ids)
    return result


def least_filled_niches(seen_videos):
    """Return configured niches with the lowest recorded ID count, in configured order."""
    # Balance only the least-filled niches so other niches do not pull further ahead.
    counts = {niche: len(seen_videos.get(niche, set())) for niche in NICHES}
    minimum_count = min(counts.values())
    return [niche for niche in NICHES if counts[niche] == minimum_count]


def save_seen_videos(seen_map):
    """Persist the per-niche seen-video map."""
    SEEN_VIDEOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Write sorted lists to keep the JSON file consistent and easy to inspect.
    payload = {niche: sorted(ids) for niche, ids in seen_map.items()}
    SEEN_VIDEOS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def get_free_local_port():
    """Reserve a free localhost port for the OAuth redirect callback."""
    # Let the operating system choose an available port for the local OAuth callback.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def get_youtube_service():
    """Modern Google-approved authentication workflow using a free local port."""
    # Build the OAuth flow from the user's configured Google API credentials.
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
    )

    redirect_port = get_free_local_port()
    flow.redirect_uri = f"http://localhost:{redirect_port}/"

    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

    # Ask the user to approve access, then receive the OAuth response locally.
    print("\n🔒 ACTION REQUIRED FOR FIRST RUN:")
    print("1. Copy and paste this exact URL into your Windows web browser:")
    print(f"\n{auth_url}\n")
    print("2. Approve the permissions in your browser.")
    print("3. Leave this terminal open; it will catch the token automatically once you click Allow.")

    credentials = flow.run_local_server(
        host='localhost',
        port=redirect_port,
        authorization_prompt_message='Authorization URL: {url}',
        open_browser=False,
    )
    # Return an authorized YouTube API client for upload operations.
    return build("youtube", "v3", credentials=credentials)


def upload_short(youtube, file_path, niche_name):
    """Programmatically posts a finalized vertical .mp4 to YouTube Shorts."""
    print(f"📤 Uploading clip to YouTube Shorts: {file_path}")
    
    # Prepare the metadata and public visibility settings for the uploaded Short.
    title = f"Mindset Shift | {niche_name} #shorts #viral"
    body = {
        "snippet": {
            "title": title[:100],
            "description": f"Automated short focusing on {niche_name}. Compiled with open-source tools.",
            "tags": [niche_name.replace(" ", ""), "viral", "podcast", "shorts"],
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": "public",  # Keep as 'public' for auto-publishing
            "selfDeclaredMadeForKids": False
        }
    }
    
    # Use resumable transfer so the YouTube API can handle large video uploads.
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    
    try:
        # Submit the video and its metadata to the YouTube Data API.
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        print(f"🚀 Successfully Uploaded! Video ID: {response.get('id')}")
    except Exception as e:
        print(f"❌ YouTube upload API failed: {str(e)}")

def trigger_clipping_engine(video_url, niche_name, youtube_service):
    """Routes the downloaded source URL into your cloned open-source clipping repo."""
    print(f"🎬 Processing clip via GPU-accelerated engine: {video_url}")
    
    # Prefer the clipping repository's environment, then the root environment.
    if REPO_VENV_PYTHON.exists():
        venv_python = str(REPO_VENV_PYTHON)
    elif ROOT_VENV_PYTHON.exists():
        venv_python = str(ROOT_VENV_PYTHON)
    else:
        venv_python = sys.executable

    cli_path = str(CLIP_REPO_DIR / "main.py")

    # Keep local output and upload bookkeeping grouped by niche.
    # The upstream clipping CLI writes under its own project-local outputs/ directory.
    # Keep a root-level folder only for local bookkeeping and upload tracking.
    output_dir = str(PROJECT_ROOT / "outputs" / "pipeline" / niche_name.replace(" ", "_"))
    os.makedirs(output_dir, exist_ok=True)

    # Configure the renderer to produce up to three subtitle-assisted vertical clips.
    cli_command = [
        venv_python, cli_path,
        "--url", video_url,
        "--clips", "3",
        "--min-clip-duration", "60",
        "--max-clip-duration", "90",
        "--use-dlp-subs",
        "--whisper-model", "tiny",
        "--whisper-device", "cuda",
        "--whisper-compute-type", "float16",
        "--no-broll",
    ]
    
    try:
        # Run the clipping engine and wait for it to finish successfully.
        subprocess.run(cli_command, check=True)
        print(f"✅ Video rendering complete for: {niche_name}")
        
        # Find rendered MP4s in the niche's output directory and upload them.
        if os.path.exists(output_dir):
            for file in os.listdir(output_dir):
                if file.endswith(".mp4"):
                    full_path = os.path.join(output_dir, file)
                    
                    # Publish each finished clip to the authenticated channel.
                    upload_short(youtube_service, full_path, niche_name)
                    
                    # Remove the local clip after the upload attempt to limit disk use.
                    os.remove(full_path)
                    
    except Exception as e:
        print(f"❌ Pipeline engine execution breakdown: {str(e)}")

def run_automated_pipeline():
    print(f"🚀 [WSL ENGINE ACTIVE] - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # Load per-niche IDs so previously processed videos can be skipped.
    seen_videos = load_seen_videos()

    # Remove stale credential files so authentication starts from a clean state.
    for old_token in ['token.json', 'token.pickle']:
        if os.path.exists(old_token):
            os.remove(old_token)

    try:
        # Authenticate once and reuse the API client for all niche uploads.
        youtube_service = get_youtube_service()
    except Exception as e:
        print(f"❌ Could not initialize YouTube API service: {str(e)}")
        return

    # Search only metadata, require Creative Commons results, and avoid downloads here.
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'js_runtimes': {'node': {}},
        'match_filter': yt_dlp.utils.match_filter_func('license*="Creative Commons"'),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Process only niches tied for the lowest count to keep coverage balanced.
        for niche in least_filled_niches(seen_videos):
            queries = NICHES[niche]
            print(f"\n📂 Scanning Niche Category: {niche}")
            seen_for_niche = seen_videos.setdefault(niche, set())
            for query in queries:
                # Fetch one top search result for this query.
                search_string = f"ytsearch1:{query}"  # Pulls the single top viral creative commons video per loop
                try:
                    result = ydl.extract_info(search_string, download=False)
                    if 'entries' in result and result['entries']:
                        entry = result['entries'][0]
                        if entry:
                            # Resolve the candidate URL and ID for deduplication.
                            video_url = entry.get('webpage_url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                            video_id = extract_video_id(video_url)

                            # Skip a video already recorded under any niche.
                            if video_id and any(
                                video_id in ids for ids in seen_videos.values()
                            ):
                                print(
                                    f"⏭️ Skipping previously processed video "
                                    f"from {SEEN_VIDEOS_PATH}: {video_id}"
                                )
                                continue

                            # Render and upload the new candidate for this niche.
                            trigger_clipping_engine(video_url, niche, youtube_service)

                            # Record the candidate ID so future runs skip it.
                            if video_id:
                                seen_for_niche.add(video_id)
                                save_seen_videos(seen_videos)

                            print(f"✅ Processed one video for {niche}; moving to next niche.")
                            break
                except Exception as e:
                    print(f"❌ Error fetching search criteria '{query}': {str(e)}")

if __name__ == "__main__":
    run_automated_pipeline()
