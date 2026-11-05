# Served video assets

Streamlit serves files in this folder at `app/static/videos/<filename>`.

For the homepage hero, place your film at `assets/videos/kerala_hero.mp4`.
The homepage copies it here automatically and uses `app/static/videos/kerala_hero.mp4`.
You may also place a pre-encoded `kerala_hero.mp4` directly in this folder for
read-only deployments where copying is not possible.

Do not add a placeholder MP4: when no video file exists the homepage uses the
local Kerala photograph fallback. A file synced from `assets/videos/` is ignored
by Git; remove it here as well if you want to revert to the photograph.
