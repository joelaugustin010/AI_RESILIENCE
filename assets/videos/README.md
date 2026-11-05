# Homepage hero video

## Where to put your film

Place your video here with exactly this name and extension:

```
assets/videos/kerala_hero.mp4
```

No code change is required. When the homepage runs, it detects the file, copies it
to `static/videos/kerala_hero.mp4` (Streamlit's servable static folder), and uses
it behind the `AI RESILIENCE` title. The copy is refreshed automatically when the
source file changes.

The video is **not** referenced from a remote URL and no placeholder `.mp4` is
committed. If no video exists at either location, the optimised Kerala photograph
`static/images/hero-kerala-fallback.jpg` is shown instead. The page never renders
a `<video>` element with a missing source.

The generated copy in `static/videos/` is ignored by Git so the film is not
committed twice. To return to the static photograph after testing a film, remove
both `assets/videos/kerala_hero.mp4` and `static/videos/kerala_hero.mp4`; removing
only the source leaves the previously synced copy in place.

## Recommended export

| Setting | Recommendation |
| --- | --- |
| Container / codec | MP4 / H.264 (AAC audio can be omitted) |
| Resolution | 1920 × 1080 (or 2560 × 1440 for large displays) |
| Length | 18–30 seconds, edited as a seamless loop |
| Frame rate | 24–30 fps |
| File size | Aim for under 20 MB; the static route accepts up to 200 MB |
| Audio | No audio needed — playback is muted |
| Encoding | `-movflags +faststart` so the first frame arrives quickly |

Example:

```bash
ffmpeg -i source.mov -an -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080" \
  -c:v libx264 -preset slow -crf 24 -pix_fmt yuv420p -movflags +faststart kerala_hero.mp4
```

## How it behaves

- `object-fit: cover` fills the entire hero at every screen size.
- A dark multi-stop gradient keeps the title and subtitle readable over any frame.
- Autoplay, loop, muted and `playsinline` are enabled.
- The local photograph is layered underneath and also used as the video poster.
- `prefers-reduced-motion: reduce` hides the video and keeps the static photograph.
- The homepage does not add a second copy of the video to the page or preload the
  full file before first paint (`preload="metadata"`).

## Deployment note

`.streamlit/config.toml` sets:

```toml
[server]
enableStaticServing = true
```

Static files are served from `static/` at `app/static/<path>`. Keep that setting
if you deploy to Streamlit Community Cloud or another Streamlit host.
