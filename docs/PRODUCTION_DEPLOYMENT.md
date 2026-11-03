# Production deployment notes

Use Docker for the production path. The dashboard app is served only through Docker in this project.

## Production command

```bash
cd ~/yt-auto-clipping
docker-compose -f docker-compose.yml up --build -d
```

The root Compose file serves the publishing dashboard. The clipping pipeline remains a separate host-side Python workflow.

## Runtime data mounts

The compose file bind-mounts the project root so the dashboard can read these directories:

- `raw/source/<video-slug>/`
- `raw/categories/<video-slug>/`
- `outputs/`
- `uploads/`
- `custom_fonts/`

## Keep secrets out of Git

Do not commit:

- `.env`
- `client_secrets.json`
- generated video files
- upload folders
- raw project exports

## Runtime policy

- Serve the dashboard with Docker only
- Keep Python for the automation pipeline and clipping jobs
- Do not start the dashboard directly with a host Python process
- Generated Shorts covers use the Cloudflare Workers AI free allocation when configured; failures fall back to a frame from the clip
