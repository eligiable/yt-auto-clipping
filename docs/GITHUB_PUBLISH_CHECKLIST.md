# GitHub Publish Checklist

Use this before pushing the project to a public repository.

## 1. Verify secrets are excluded

Check that these files are ignored:

- `.env`
- `.env.*` (except examples)
- `client_secrets.json`
- any API keys or local tokens

## 2. Confirm the repo is clean

```bash
cd ~/youtube_automation
git status
```

## 3. Confirm the public-facing files are present

Make sure these are included:

- `README.md`
- `docs/HOST_SETUP.md`
- `docs/DEPLOYMENT.md`
- `docs/PRODUCTION_DEPLOYMENT.md`
- `docs/GITHUB_PUBLISH_CHECKLIST.md`
- `raw/README.md`
- `setup_linux_host.sh`
- `opensource-clipping/requirements.txt`
- `opensource-clipping/.env.example`

## 4. Make sure the project still has the right structure

```bash
find . -maxdepth 2 -type d | sort
```

Expected essentials:

- `custom_fonts/`
- `raw/source/`
- `raw/categories/`
- `opensource-clipping/`
- `outputs/` (optional local generated directory)

## 5. Decide whether to keep large media in Git

By default, large generated media should stay local.

Recommended public-safe strategy:

- keep `raw/categories/` only if final clips are small
- keep `raw/source/` local
- keep `outputs/` local
- use Git LFS for any video assets that must be versioned

## 6. Commit and push

```bash
git add .
git commit -m "Initial project setup and deployment docs"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

## 7. After pushing

- open the repo on GitHub
- verify the README renders correctly
- verify secrets are not present
- verify no private API keys or client credentials are checked in

## 8. Optional: use Git LFS for large asset files

If you want to keep video files in Git history:

```bash
git lfs install
git lfs track "*.mp4"
git lfs track "*.mov"
git lfs track "*.mkv"
```

Then commit the `.gitattributes` file as well.

## 9. Final note

This repo is best published as a setup-and-deployment guide plus project skeleton, while the actual raw media and secret files remain local or are managed through Git LFS or a private repository.
