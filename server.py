from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import quote, urlsplit
import json
import mimetypes
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'dashboard_index.html'

ALLOWED_EXTS = {
    '.mp4', '.mov', '.mkv', '.webm',
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'
}
EXCLUDED_FILES = {'seen_videos.json'}
PLATFORM_FIELDS = {
    'youtube_title_final', 'youtube_description_final', 'youtube_tags_final',
    'youtube_upload_status', 'youtube_video_id',
    'tiktok_title_id_final', 'tiktok_caption_final', 'tiktok_caption_id_final',
    'tiktok_upload_status',
    'instagram_title_final', 'instagram_caption_final', 'instagram_upload_status',
}
UPLOAD_STATUSES = {'draft', 'ready', 'uploaded', 'scheduled', 'failed'}


def collect_library_items():
    items = []
    for folder in ['raw', 'outputs', 'uploads', 'custom_fonts']:
        base = ROOT / folder
        if not base.exists():
            continue
        for file_path in sorted(base.rglob('*')):
            if not file_path.is_file():
                continue
            if file_path.name in EXCLUDED_FILES:
                continue
            ext = file_path.suffix.lower()
            if ext not in ALLOWED_EXTS:
                continue
            rel = file_path.relative_to(base).as_posix()
            items.append({
                'path': rel,
                'type': ext.lstrip('.'),
                'size': file_path.stat().st_size,
                'folder': folder,
            })
    return items


def _raw_url(path: Path) -> str:
    raw_root = (ROOT / 'raw').resolve()
    relative = path.resolve().relative_to(raw_root).as_posix()
    return '/raw/' + quote(relative, safe='/')


def _resolve_project_path(value: str) -> Path | None:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT / candidate

    try:
        resolved = candidate.resolve()
        resolved.relative_to(ROOT.resolve())
        return resolved
    except ValueError:
        parts = candidate.parts
        try:
            raw_index = parts.index('raw')
        except ValueError:
            return None
        rebased = (ROOT / Path(*parts[raw_index:])).resolve()
        try:
            rebased.relative_to(ROOT.resolve())
        except ValueError:
            return None
        return rebased


def collect_jobs():
    categories = ROOT / 'raw' / 'categories'
    if not categories.exists():
        return {'jobs': [], 'summary': {'jobs': 0, 'clips': 0, 'ready': 0, 'uploaded': 0}}

    jobs = []
    for manifest_path in sorted(categories.rglob('render_manifest.json')):
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(manifest, list):
            continue

        job_dir = manifest_path.parent
        relative_job_dir = job_dir.relative_to(categories).as_posix()
        job_id = 'legacy' if relative_job_dir == '.' else relative_job_dir
        settings_path = job_dir / 'clip_settings.json'
        try:
            saved_settings = json.loads(settings_path.read_text(encoding='utf-8')) if settings_path.exists() else {}
        except (OSError, json.JSONDecodeError):
            saved_settings = {}
        saved_clips = saved_settings.get('clips', {})
        metadata_path = job_dir / 'metadata_preview.json'
        try:
            metadata = json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.exists() else []
        except (OSError, json.JSONDecodeError):
            metadata = []
        metadata_by_rank = {str(row.get('rank')): row for row in metadata if isinstance(row, dict)}

        if job_id == 'legacy':
            source_path = ROOT / 'raw' / 'source' / 'video_asli.mp4'
        else:
            source_path = ROOT / 'raw' / 'source' / job_id / 'video_asli.mp4'
        source_preview_path = source_path.with_name('video_asli_preview.mp4')

        clips = []
        for row in manifest:
            if not isinstance(row, dict):
                continue
            rank = row.get('rank')
            clip = dict(row)
            clip.update({key: value for key, value in metadata_by_rank.get(str(rank), {}).items() if key not in clip})
            clip.update(saved_clips.get(str(rank), {}))
            video_path = _resolve_project_path(row.get('video_path', ''))
            thumbnail_path = _resolve_project_path(row.get('thumbnail_path', ''))
            clip['video_url'] = _raw_url(video_path) if video_path and video_path.is_file() else None
            clip['thumbnail_url'] = _raw_url(thumbnail_path) if thumbnail_path and thumbnail_path.is_file() else None
            clip['instagram_title_final'] = clip.get('instagram_title_final') or clip.get('youtube_title_final', '')
            clip['instagram_caption_final'] = clip.get('instagram_caption_final') or clip.get('tiktok_caption_final', '')
            clip['instagram_upload_status'] = clip.get('instagram_upload_status', 'draft')
            clip['youtube_upload_status'] = clip.get('youtube_upload_status', 'draft')
            clip['tiktok_upload_status'] = clip.get('tiktok_upload_status', 'draft')
            clips.append(clip)

        source_url = next((clip.get('source_url') for clip in clips if clip.get('source_url')), '')
        try:
            source_url_path = _raw_url(source_preview_path if source_preview_path.is_file() else source_path) if source_path.is_file() else None
            source_download_url = _raw_url(source_path) if source_path.is_file() else None
        except ValueError:
            source_url_path = None
            source_download_url = None
        jobs.append({
            'id': job_id,
            'title': 'Current run' if job_id == 'legacy' else job_id.replace('_', ' '),
            'source_url': source_url,
            'source_video_url': source_url_path,
            'source_download_url': source_download_url,
            'created_at': manifest_path.stat().st_mtime,
            'clips': clips,
        })

    jobs.sort(key=lambda job: job['created_at'], reverse=True)
    total_clips = sum(len(job['clips']) for job in jobs)
    return {
        'jobs': jobs,
        'summary': {
            'jobs': len(jobs),
            'clips': total_clips,
            'ready': sum(clip.get(f'{platform}_upload_status') == 'ready' for job in jobs for clip in job['clips'] for platform in ('youtube', 'tiktok', 'instagram')),
            'uploaded': sum(clip.get(f'{platform}_upload_status') == 'uploaded' for job in jobs for clip in job['clips'] for platform in ('youtube', 'tiktok', 'instagram')),
        },
    }


def save_clip_settings(payload):
    job_id = str(payload.get('job_id', ''))
    rank = str(payload.get('rank', ''))
    category_root = (ROOT / 'raw' / 'categories').resolve()
    job_dir = category_root if job_id == 'legacy' else (category_root / job_id).resolve()
    if not job_dir.is_relative_to(category_root):
        raise ValueError('Invalid job id.')

    manifest_path = job_dir / 'render_manifest.json'
    if not manifest_path.is_file():
        raise FileNotFoundError('Job manifest not found.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not any(str(row.get('rank')) == rank for row in manifest if isinstance(row, dict)):
        raise ValueError('Clip rank not found in job.')

    fields = payload.get('fields')
    if not isinstance(fields, dict):
        raise ValueError('Clip fields must be an object.')
    updates = {key: value for key, value in fields.items() if key in PLATFORM_FIELDS}
    for field in ('youtube_upload_status', 'tiktok_upload_status', 'instagram_upload_status'):
        if field in updates and updates[field] not in UPLOAD_STATUSES:
            raise ValueError(f'Invalid status for {field}.')
    if 'youtube_tags_final' in updates:
        value = updates['youtube_tags_final']
        updates['youtube_tags_final'] = value if isinstance(value, list) else [tag.strip() for tag in str(value).split(',') if tag.strip()]

    settings_path = job_dir / 'clip_settings.json'
    try:
        settings = json.loads(settings_path.read_text(encoding='utf-8')) if settings_path.exists() else {}
    except json.JSONDecodeError:
        settings = {}
    settings.setdefault('clips', {}).setdefault(rank, {}).update(updates)
    settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')

    for row in manifest:
        if isinstance(row, dict) and str(row.get('rank')) == rank:
            row.update(updates)
            break
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'saved': True}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        return

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, file_path: Path):
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, 'Not found')
            return
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = 'application/octet-stream'
        file_size = file_path.stat().st_size
        start = 0
        end = file_size - 1
        status = 200
        range_header = self.headers.get('Range')
        if range_header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', range_header.strip())
            if not match or (not match.group(1) and not match.group(2)):
                self.send_error(416, 'Invalid byte range')
                return
            if match.group(1):
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else end
            else:
                suffix_length = int(match.group(2))
                start = max(0, file_size - suffix_length)
            if start >= file_size or end < start:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{file_size}')
                self.end_headers()
                return
            end = min(end, file_size - 1)
            status = 206

        content_length = end - start + 1
        self.send_response(status)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Length', str(content_length))
        self.send_header('Accept-Ranges', 'bytes')
        if status == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
        self.end_headers()
        with file_path.open('rb') as media_file:
            media_file.seek(start)
            remaining = content_length
            while remaining:
                chunk = media_file.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self):
        parsed = urlsplit(self.path)
        path = parsed.path

        if path == '/':
            self.serve_file(INDEX)
            return

        if path == '/api/library':
            self.send_json({'items': collect_library_items()})
            return

        if path == '/api/jobs':
            self.send_json(collect_jobs())
            return

        if path.startswith('/raw/'):
            target = ROOT / path.lstrip('/')
            self.serve_file(target)
            return

        if path.startswith('/outputs/') or path.startswith('/uploads/') or path.startswith('/custom_fonts/'):
            target = ROOT / path.lstrip('/')
            self.serve_file(target)
            return

        if path.startswith('/api/'):
            self.send_json({'error': 'not found'}, 404)
            return

        target = ROOT / path.lstrip('/')
        if target.exists() and target.is_file():
            self.serve_file(target)
            return

        self.send_error(404, 'Not found')

    def do_POST(self):
        parsed = urlsplit(self.path)
        if parsed.path != '/api/clip-settings':
            self.send_json({'error': 'not found'}, 404)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            payload = json.loads(self.rfile.read(length))
            self.send_json(save_clip_settings(payload))
        except (ValueError, json.JSONDecodeError, FileNotFoundError) as exc:
            self.send_json({'error': str(exc)}, 400)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8001'))
    server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    print(f'Serving dashboard on http://0.0.0.0:{port}')
    server.serve_forever()
