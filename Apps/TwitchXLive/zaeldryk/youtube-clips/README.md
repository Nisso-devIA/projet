# YouTube clips pipeline (Twitch VOD → Shorts + classic best-of)

## What it does

After each real live (title not matching skip pattern):

1. Enqueue a job when the stream goes `ending` / `offline`
2. Download the Twitch VOD (720p)
3. Score highlights from chat density
4. Render **5 Shorts** (9:16, ~40s) + **1 classic** (16:9, 10–15 min compilation)
5. Mix local NCS / royalty-free music + credit in the YouTube description
6. Upload via YouTube Data API (or dry-run)

Skip titles (default): `ending`, `offline`, `test`, `end`  
While live, the orchestrator stores `state/last_good_live_title.txt` so a rename to “ending” does not poison the job.

## One-time setup

### 1. System packages

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
pip3 install --user -r /home/ubuntu/zaeldryk/youtube-clips/requirements.txt
# yt-dlp:
pip3 install --user -U yt-dlp
```

### 2. YouTube OAuth (once, on a PC with a browser)

1. Google Cloud Console → enable **YouTube Data API v3**
2. Create OAuth client (Desktop) → download `client_secret.json`
3. Run:

```bash
python3 tools/youtube-oauth-setup.py \
  --client-secrets ./client_secret.json \
  --out ./youtube-oauth.json
```

4. Copy to VPS:

```bash
scp youtube-oauth.json ubuntu@VPS:/home/ubuntu/zaeldryk/config/youtube-oauth.json
ssh ubuntu@VPS 'chmod 600 /home/ubuntu/zaeldryk/config/youtube-oauth.json'
```

Optional: also copy client secrets to `config/youtube-client-secrets.json` for token refresh tooling.

### 3. NCS / nocopyright music

Put audio files under `youtube-clips/music/` and edit `music/manifest.json`:

```json
[
  {
    "file": "my-track.mp3",
    "title": "Song Name",
    "artist": "Artist",
    "credit_url": "https://ncs.io/...",
    "license": "NCS"
  }
]
```

Uploads are refused if the manifest has no usable tracks (file missing or no title/artist).

### 4. Config

```bash
cp config/youtube-clips.env.example config/youtube-clips.env
# edit: YOUTUBE_CLIPS_DRY_RUN=1 for first run
```

## Deploy on VPS

From the synced `zaeldryk` tree on the VPS:

```bash
bash /home/ubuntu/zaeldryk/tools/deploy-youtube-clips.sh /home/ubuntu/zaeldryk
```

This creates `/home/ubuntu/backups/YYYY-MM-DD_HHMM_youtube-clips/`, installs systemd timer (every 30 min), and restarts `zaeldryk-live` if present.

## Dry-run test

```bash
# in config/youtube-clips.env
YOUTUBE_CLIPS_DRY_RUN=1
YOUTUBE_CLIPS_ENABLED=1

# manual run
/home/ubuntu/zaeldryk/youtube-clips/run-youtube-clips.sh
# or
sudo systemctl start zaeldryk-youtube-clips.service
tail -f /home/ubuntu/zaeldryk/logs/youtube-clips.log
```

Outputs land in `youtube-clips/work/<vod_id>/out/` without uploading.

## Manual enqueue

```bash
# uses last_good_live_title if set
python3 /home/ubuntu/zaeldryk/youtube-clips/enqueue_job.py

# or force fields
YOUTUBE_CLIPS_JOB_TITLE='Mon vrai titre' \
YOUTUBE_CLIPS_JOB_GAME='GTA V' \
python3 /home/ubuntu/zaeldryk/youtube-clips/enqueue_job.py
```

## Ops notes

- Disk: keep ~10–15 Go free during a run; VOD file is deleted after success
- Logs: `logs/youtube-clips.log`
- State DB: `state/youtube-clips.sqlite`
- Queue: `state/youtube-clips-queue/*.job`
- Timer: `systemctl list-timers zaeldryk-youtube-clips.timer`
