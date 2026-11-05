"""Cinematic Kerala homepage for AI RESILIENCE.

The page is intentionally image-led: Kerala's landscapes, the pressures they
face, the intelligence chain that connects them, and direct routes into the
existing analytical workspaces.

Hero film
---------
Drop your own footage at ``assets/videos/kerala_hero.mp4``. On the next rerun
the file is made available through Streamlit's static file route and used as a
muted, looping, cover-fit background. Until then - or if the file is removed -
the optimised local photograph in ``static/images/`` is shown instead. No
remote video URL and no placeholder video file is referenced.
"""

from pathlib import Path
import shutil

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
STATIC_IMAGES = "app/static/images"
ASSETS_VIDEO = ROOT / "assets" / "videos" / "kerala_hero.mp4"
STATIC_VIDEO = ROOT / "static" / "videos" / "kerala_hero.mp4"
STATIC_VIDEO_URL = "app/static/videos/kerala_hero.mp4"


def _img(filename: str) -> str:
    return f"{STATIC_IMAGES}/{filename}"


def _sync_hero_video() -> str | None:
    """Return a servable hero-video URL only when a real local file exists.

    ``assets/videos/kerala_hero.mp4`` is the documented drop-in location. The
    copy into ``static/videos`` is what Streamlit can serve; it happens only
    when the source file is new or has changed. Nothing is fabricated here.
    """

    try:
        if ASSETS_VIDEO.is_file() and ASSETS_VIDEO.stat().st_size > 0:
            needs_copy = True
            if STATIC_VIDEO.is_file() and STATIC_VIDEO.stat().st_size > 0:
                same_size = STATIC_VIDEO.stat().st_size == ASSETS_VIDEO.stat().st_size
                same_time = int(STATIC_VIDEO.stat().st_mtime) >= int(ASSETS_VIDEO.stat().st_mtime)
                needs_copy = not (same_size and same_time)
            if needs_copy:
                STATIC_VIDEO.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ASSETS_VIDEO, STATIC_VIDEO)
    except OSError:
        # A read-only deployment can still use a pre-placed file in static/.
        pass

    if STATIC_VIDEO.is_file() and STATIC_VIDEO.stat().st_size > 0:
        return STATIC_VIDEO_URL
    return None


def _svg(paths: str, size: int = 20) -> str:
    return (
        f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" '
        'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{paths}</svg>'
    )


ICON_COMPASS = _svg(
    '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5 5-2Z"/>'
)
ICON_PLACE = _svg(
    '<path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>'
)
ICON_HOSPITAL = _svg(
    '<path d="M4 21V7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v14"/><path d="M2 21h20"/>'
    '<path d="M9 21v-5h6v5"/><path d="M12 8v5M9.5 10.5h5"/>'
)
ICON_BLUEPRINT = _svg(
    '<path d="M3 21h18"/><path d="M5 21V8l7-4 7 4v13"/>'
    '<path d="M9 21v-6h6v6"/><path d="M9 11h6"/>'
)
ICON_SHIELD = _svg(
    '<path d="M12 22s8-3.6 8-10V5l-8-3-8 3v7c0 6.4 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>'
)
ICON_FLOOD = _svg(
    '<path d="M2 7c.7.7 1.5 1.2 2.6 1.2 2.4 0 2.4-2.2 4.9-2.2s2.4 2.2 4.9 2.2S17 6 19.4 6c1.1 0 1.9.5 2.6 1.2"/>'
    '<path d="M2 13c.7.7 1.5 1.2 2.6 1.2 2.4 0 2.4-2.2 4.9-2.2s2.4 2.2 4.9 2.2S17 12 19.4 12c1.1 0 1.9.5 2.6 1.2"/>'
    '<path d="M2 19c.7.7 1.5 1.2 2.6 1.2 2.4 0 2.4-2.2 4.9-2.2s2.4 2.2 4.9 2.2S17 18 19.4 18c1.1 0 1.9.5 2.6 1.2"/>'
)
ICON_LANDSLIDE = _svg(
    '<path d="m3 20 5.5-9 3 4 3-6L21 20H3Z"/><path d="m8.5 11 .8-4 2.2 2"/>'
    '<path d="M15.5 4.5v1M18.5 6.5l-.7.7M13 7l.7.7"/>'
)
ICON_CYCLONE = _svg(
    '<path d="M12 2a10 10 0 1 0 10 10"/><path d="M12 6a6 6 0 1 0 6 6"/>'
    '<path d="M12 10a2 2 0 1 0 2 2"/>'
)
ICON_FACTORY = _svg(
    '<path d="M2 21h20"/><path d="M4 21V9l6 4V9l6 4V4h4v17"/>'
    '<path d="M7 17h1M12 17h1M17 17h1"/>'
)
ICON_RAIN = _svg(
    '<path d="M4.5 14.5A4.5 4.5 0 0 1 5.6 5.7 5.7 5.7 0 0 1 16.6 5a4.2 4.2 0 0 1 2.2 8"/>'
    '<path d="M8 17.5v2M12 16.5v3M16 17.5v2"/>'
)
ICON_LEAF = _svg(
    '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10Z"/>'
    '<path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.5 12 13 13 12"/>'
)

VIDEO_URL = _sync_hero_video()
VIDEO_MARKUP = ""
if VIDEO_URL:
    # Keep the video tag on one line. A blank line inside the surrounding raw
    # HTML block makes Markdown start a new block, which can turn the following
    # nested spans into a visible code fragment.
    VIDEO_MARKUP = (
        f'<video class="ar-cine-video" autoplay muted loop playsinline preload="metadata" '
        f'poster="{_img("hero-kerala-fallback.jpg")}" tabindex="-1" aria-hidden="true">'
        f'<source src="{VIDEO_URL}" type="video/mp4">'
        "</video>"
    )


st.markdown(
    """
    <style>
    /* ============================================================
       AI RESILIENCE - Kerala homepage
       Scoped below the shared design system defined in app.py.
       ============================================================ */
    .ar-home-copy { max-width: 860px; }

    /* A slow documentary sequence: flooded road, Western Ghats monsoon,
       landslide scar and the coast before heavy rain. Each frame holds for
       roughly eight seconds, with a long crossfade and a restrained push-in. */
    @keyframes arSlideCycle {
      0%   { opacity: 1; transform: scale(1.02) translate3d(0, 0, 0); }
      21%  { opacity: 1; transform: scale(1.055) translate3d(-.6%, -.4%, 0); }
      28%  { opacity: 0; transform: scale(1.075) translate3d(-.9%, -.6%, 0); }
      100% { opacity: 0; transform: scale(1.075) translate3d(-.9%, -.6%, 0); }
    }
    @keyframes arRise {
      from { opacity: 0; transform: translateY(16px); }
      to   { opacity: 1; transform: none; }
    }
    @keyframes arPulse {
      0%   { box-shadow: 0 0 0 0 rgba(66, 224, 193, .45); }
      70%  { box-shadow: 0 0 0 8px rgba(66, 224, 193, 0); }
      100% { box-shadow: 0 0 0 0 rgba(66, 224, 193, 0); }
    }

    /* ---------- Cinematic hero ---------- */
    .ar-cine-hero {
      position: relative;
      isolation: isolate;
      display: flex;
      flex-direction: column;
      min-height: clamp(540px, 72vh, 760px);
      margin: .15rem 0 0;
      padding: clamp(1.5rem, 4vw, 3.2rem);
      padding-bottom: clamp(8.2rem, 12vw, 10.2rem);
      overflow: hidden;
      border: 1px solid rgba(126, 208, 202, .26);
      border-radius: 28px;
      background: #071c2a;
      box-shadow: 0 30px 80px rgba(0, 0, 0, .38);
    }
    .ar-cine-media, .ar-cine-slide, .ar-cine-poster, .ar-cine-video {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
    }
    /* Streamlit's markdown image rule (`… img { object-fit: scale-down }`)
       outranks a single class selector, so both media layers are scoped and
       pinned to cover explicitly. */
    .ar-cine-hero .ar-cine-slide {
      z-index: 0;
      object-fit: cover !important;
      opacity: 0;
      filter: saturate(.96) contrast(1.04);
      animation: arSlideCycle 32s cubic-bezier(.45, .05, .55, .95) infinite;
      will-change: opacity, transform;
    }
    .ar-cine-hero .ar-slide-a { object-position: center 56%; animation-delay: 0s; }
    .ar-cine-hero .ar-slide-b { object-position: center 46%; animation-delay: -8s; }
    .ar-cine-hero .ar-slide-c { object-position: center 52%; animation-delay: -16s; }
    .ar-cine-hero .ar-slide-d { object-position: center 50%; animation-delay: -24s; }
    .ar-cine-hero .ar-cine-video {
      z-index: 1;
      object-fit: cover !important;
      object-position: center;
    }
    .ar-cine-scrim {
      position: absolute;
      inset: 0;
      z-index: 2;
      background:
        linear-gradient(90deg, rgba(3, 15, 23, .95) 0%, rgba(4, 22, 32, .82) 40%, rgba(4, 26, 36, .30) 68%, rgba(4, 22, 32, .56) 100%),
        linear-gradient(180deg, rgba(4, 17, 26, .40) 0%, rgba(4, 17, 26, .02) 30%, rgba(3, 14, 21, .90) 100%),
        radial-gradient(ellipse at 50% 45%, transparent 18%, rgba(3, 14, 21, .22) 100%);
    }
    .ar-cine-vignette {
      position: absolute;
      inset: 0;
      z-index: 3;
      pointer-events: none;
      box-shadow: inset 0 0 150px 34px rgba(0, 0, 0, .48);
    }
    .ar-cine-grain {
      position: absolute;
      inset: 0;
      z-index: 4;
      pointer-events: none;
      opacity: .05;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.9'/%3E%3C/svg%3E");
    }
    .ar-cine-inner {
      position: relative;
      z-index: 5;
      display: flex;
      flex: 1;
      flex-direction: column;
      justify-content: center;
      width: 100%;
      max-width: 960px;
      padding: clamp(1rem, 3vw, 2rem) 0 0;
    }
    .ar-cine-topline {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: .8rem 1.4rem;
      margin-bottom: clamp(1.4rem, 3vw, 2.4rem);
    }
    .ar-cine-kicker {
      display: inline-flex;
      align-items: center;
      gap: .6rem;
      color: #b9f7ec;
      font-size: .72rem;
      font-weight: 800;
      letter-spacing: .17em;
      text-transform: uppercase;
    }
    .ar-live-dot {
      display: inline-block;
      width: .55rem;
      height: .55rem;
      border-radius: 50%;
      background: #42e0c1;
      animation: arPulse 2.8s ease-out infinite;
    }
    .ar-cine-coord {
      color: #9fc3c8;
      font-size: .68rem;
      letter-spacing: .12em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .ar-cine-title {
      margin: 0 !important;
      color: #fff !important;
      font-size: clamp(2.85rem, 7.1vw, 6.35rem) !important;
      font-weight: 850 !important;
      line-height: .92 !important;
      letter-spacing: -.055em !important;
      text-shadow: 0 8px 34px rgba(0, 0, 0, .38);
      animation: arRise .7s var(--ar-ease) both;
    }
    .ar-cine-title span {
      background: linear-gradient(100deg, #ffffff 4%, #c8fff3 42%, #42e0c1 100%);
      -webkit-background-clip: text;
      background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .ar-cine-sub {
      max-width: 760px;
      margin: clamp(1.1rem, 2.4vw, 1.7rem) 0 0;
      color: #f0fffc;
      font-size: clamp(1.1rem, 1.75vw, 1.42rem);
      font-weight: 550;
      line-height: 1.45;
      letter-spacing: -.012em;
      text-shadow: 0 2px 16px rgba(0, 0, 0, .58);
      animation: arRise .7s .08s var(--ar-ease) both;
    }
    .ar-cine-desc {
      max-width: 720px;
      margin: .9rem 0 0;
      color: #c3dde1;
      font-size: clamp(.92rem, 1.1vw, 1rem);
      line-height: 1.7;
      text-shadow: 0 1px 12px rgba(0, 0, 0, .52);
      animation: arRise .7s .16s var(--ar-ease) both;
    }
    .ar-cine-chips {
      display: flex;
      flex-wrap: wrap;
      gap: .45rem;
      margin-top: 1.25rem;
      animation: arRise .7s .24s var(--ar-ease) both;
    }
    .ar-cine-chips span {
      border: 1px solid rgba(255, 255, 255, .20);
      border-radius: 999px;
      background: rgba(8, 36, 47, .38);
      backdrop-filter: blur(8px);
      color: #e7fffa;
      padding: .36rem .72rem;
      font-size: .73rem;
      letter-spacing: .015em;
    }
    .ar-cine-foot {
      position: absolute;
      z-index: 5;
      left: clamp(1.5rem, 4vw, 3.2rem);
      right: clamp(1.5rem, 4vw, 3.2rem);
      bottom: 1.25rem;
      display: flex;
      align-items: center;
      gap: .8rem;
      color: #a7c6cb;
      font-size: .66rem;
      font-weight: 650;
      letter-spacing: .16em;
      text-transform: uppercase;
    }
    .ar-scroll-line {
      flex: 1;
      height: 1px;
      max-width: 130px;
      background: linear-gradient(90deg, rgba(66, 224, 193, .7), rgba(66, 224, 193, 0));
    }
    .ar-cine-foot .ar-foot-right { margin-left: auto; }

    /* Two primary actions sit in a glass dock overlapping the hero edge. */
    .st-key-ar-hero-ctas {
      position: relative;
      z-index: 6;
      margin-top: clamp(-5.6rem, -6vw, -4.2rem);
      padding: 0 clamp(1.4rem, 4vw, 3.2rem);
    }
    .st-key-ar-hero-ctas [data-testid="stButton"] > button {
      min-height: 3.15rem;
      border-radius: 12px;
      font-size: .94rem;
      letter-spacing: .01em;
    }
    .st-key-ar-hero-ctas [data-testid="stButton"] > button[kind="primary"] {
      box-shadow: 0 14px 34px rgba(66, 224, 193, .20);
    }
    .st-key-ar-hero-ctas [data-testid="stButton"] > button[kind="secondary"] {
      background: rgba(5, 21, 32, .72) !important;
      border-color: rgba(255, 255, 255, .30) !important;
      color: #f4ffff !important;
      backdrop-filter: blur(12px);
    }
    .ar-cta-note {
      display: flex;
      align-items: center;
      min-height: 3.15rem;
      color: #a9c5ca;
      font-size: .8rem;
      line-height: 1.5;
    }
    .ar-cta-note strong { color: #e7fffa; }

    /* ---------- Signal strip ---------- */
    .ar-signal {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin: clamp(2rem, 4vw, 3.2rem) 0 0;
      border-top: 1px solid var(--ar-border);
      border-bottom: 1px solid var(--ar-border);
    }
    .ar-signal > div {
      padding: 1.05rem 1.2rem 1.1rem;
      border-left: 1px solid rgba(130, 190, 199, .14);
    }
    .ar-signal > div:first-child { border-left: 0; padding-left: 0; }
    .ar-signal strong {
      display: block;
      color: #f0ffff;
      font-size: clamp(1.35rem, 2.2vw, 1.72rem);
      font-weight: 800;
      letter-spacing: -.035em;
      line-height: 1;
    }
    .ar-signal span {
      display: block;
      margin-top: .35rem;
      color: #42e0c1;
      font-size: .66rem;
      font-weight: 800;
      letter-spacing: .15em;
      text-transform: uppercase;
    }
    .ar-signal p {
      margin: .35rem 0 0;
      color: #91adb5;
      font-size: .78rem;
      line-height: 1.5;
    }

    /* ---------- Story headers ---------- */
    .ar-story {
      max-width: 860px;
      margin: clamp(3.4rem, 6vw, 5rem) 0 1.3rem;
    }
    .ar-overline {
      display: inline-flex;
      align-items: center;
      gap: .55rem;
      color: var(--ar-sand);
      font-size: .7rem;
      font-weight: 800;
      letter-spacing: .18em;
      text-transform: uppercase;
    }
    .ar-overline:before {
      content: "";
      width: 1.7rem;
      height: 1px;
      background: currentColor;
      opacity: .7;
    }
    .ar-story h2 {
      margin: .65rem 0 .75rem !important;
      color: #f2ffff !important;
      font-size: clamp(2rem, 3.7vw, 3.25rem) !important;
      line-height: 1.04 !important;
      letter-spacing: -.04em !important;
    }
    .ar-story p {
      max-width: 700px;
      margin: 0;
      color: #b4cdd2;
      font-size: 1rem;
      line-height: 1.7;
    }
    .ar-fineprint {
      margin: 1rem 0 0;
      color: #8fa9b0;
      font-size: .72rem;
      line-height: 1.55;
      letter-spacing: .01em;
    }

    /* ---------- Beauty gallery ---------- */
    .ar-gallery {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      grid-auto-rows: 215px;
      gap: .85rem;
      margin-top: 1.5rem;
    }
    .ar-tile {
      position: relative;
      overflow: hidden;
      margin: 0;
      border: 1px solid rgba(130, 190, 199, .20);
      border-radius: 18px;
      background: #0a2030;
      box-shadow: 0 14px 34px rgba(0, 0, 0, .20);
    }
    .ar-tile img {
      width: 100%;
      height: 100%;
      display: block;
      object-fit: cover;
      filter: saturate(.96) contrast(1.03);
      transition: transform .75s var(--ar-ease), filter .75s var(--ar-ease);
    }
    .ar-tile:after {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(3, 14, 21, 0) 34%, rgba(3, 14, 21, .12) 52%, rgba(3, 14, 21, .88) 100%);
      pointer-events: none;
    }
    .ar-tile:hover img { transform: scale(1.045); filter: saturate(1.08) contrast(1.05); }
    .ar-tile figcaption {
      position: absolute;
      z-index: 2;
      left: 0;
      right: 0;
      bottom: 0;
      padding: 1rem 1.05rem;
    }
    .ar-tile figcaption strong {
      display: block;
      color: #fff;
      font-size: 1rem;
      font-weight: 760;
      letter-spacing: -.012em;
    }
    .ar-tile figcaption span {
      display: block;
      margin-top: .16rem;
      color: #c5dde1;
      font-size: .74rem;
      line-height: 1.45;
    }
    .ar-tile-tag {
      position: absolute;
      z-index: 2;
      top: .8rem;
      left: .8rem;
      border: 1px solid rgba(255, 255, 255, .22);
      border-radius: 999px;
      background: rgba(3, 18, 27, .46);
      backdrop-filter: blur(7px);
      color: #eafffb;
      padding: .2rem .55rem;
      font-size: .62rem;
      font-weight: 700;
      letter-spacing: .12em;
      text-transform: uppercase;
    }
    .ar-t-backwaters { grid-column: span 2; grid-row: span 2; }
    .ar-t-ghats { grid-column: span 2; }
    .ar-t-forest { grid-column: span 2; }
    .ar-t-city { grid-column: span 2; }

    /* ---------- Threats ---------- */
    .ar-threat {
      position: relative;
      isolation: isolate;
      overflow: hidden;
      margin: clamp(3.4rem, 6vw, 5rem) 0 0;
      border: 1px solid rgba(130, 190, 199, .24);
      border-radius: 26px;
      box-shadow: 0 26px 66px rgba(0, 0, 0, .30);
    }
    .ar-threat .ar-threat-bg {
      position: absolute;
      inset: 0;
      z-index: 0;
      width: 100%;
      height: 100%;
      object-fit: cover !important;
      object-position: center;
      filter: saturate(.72) contrast(1.06) brightness(.78);
    }
    .ar-threat-scrim {
      position: absolute;
      inset: 0;
      z-index: 1;
      background:
        linear-gradient(115deg, rgba(3, 14, 21, .96) 0%, rgba(4, 22, 32, .88) 48%, rgba(6, 35, 44, .72) 100%),
        linear-gradient(0deg, rgba(3, 14, 21, .72), rgba(3, 14, 21, 0) 60%);
    }
    .ar-threat-inner {
      position: relative;
      z-index: 2;
      padding: clamp(1.6rem, 4vw, 3.2rem);
    }
    .ar-threat .ar-story { margin-top: 0; }
    .ar-threat .ar-story p { color: #bdd5d9; }
    .ar-hazards {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: .8rem;
      margin-top: 1.6rem;
    }
    .ar-hazard {
      padding: 1.05rem 1.08rem;
      border: 1px solid rgba(255, 255, 255, .11);
      border-radius: 16px;
      background: rgba(255, 255, 255, .045);
      backdrop-filter: blur(8px);
      transition: transform .2s var(--ar-ease), background .2s var(--ar-ease), border-color .2s var(--ar-ease);
    }
    .ar-hazard:hover {
      transform: translateY(-3px);
      border-color: rgba(66, 224, 193, .32);
      background: rgba(255, 255, 255, .07);
    }
    .ar-hazard-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 38px;
      height: 38px;
      margin-bottom: .7rem;
      border: 1px solid rgba(66, 224, 193, .20);
      border-radius: 11px;
      background: rgba(66, 224, 193, .10);
      color: #7ef1da;
    }
    .ar-hazard h3 {
      margin: 0 0 .3rem !important;
      color: #f2ffff !important;
      font-size: .98rem !important;
      letter-spacing: -.015em !important;
    }
    .ar-hazard p {
      margin: 0;
      color: #b8d0d5;
      font-size: .81rem;
      line-height: 1.55;
    }

    /* ---------- Why it matters ---------- */
    .ar-why {
      margin-top: clamp(3.4rem, 6vw, 5rem);
      padding: clamp(1.5rem, 3.6vw, 3rem);
      border: 1px solid rgba(130, 190, 199, .22);
      border-radius: 26px;
      background:
        radial-gradient(ellipse at 88% 8%, rgba(66, 224, 193, .10), transparent 22rem),
        linear-gradient(155deg, rgba(14, 45, 64, .88), rgba(7, 26, 40, .94));
      box-shadow: 0 24px 60px rgba(0, 0, 0, .24);
    }
    .ar-flow {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: .9rem;
      margin: 2rem 0 0;
      padding: 0;
      list-style: none;
    }
    .ar-flow-step {
      padding: 1rem .95rem 1.1rem;
      border-top: 1px solid rgba(66, 224, 193, .52);
      border-radius: 0 0 12px 12px;
      background: linear-gradient(180deg, rgba(66, 224, 193, .055), rgba(66, 224, 193, 0));
      transition: background .2s var(--ar-ease), transform .2s var(--ar-ease);
    }
    .ar-flow-step:hover {
      transform: translateY(-2px);
      background: linear-gradient(180deg, rgba(66, 224, 193, .10), rgba(66, 224, 193, 0));
    }
    .ar-step-no {
      display: block;
      color: #4be5c8;
      font-size: .66rem;
      font-weight: 800;
      letter-spacing: .18em;
    }
    .ar-flow-step h3 {
      margin: .5rem 0 .3rem !important;
      color: #f0ffff !important;
      font-size: 1rem !important;
    }
    .ar-flow-step p {
      margin: 0;
      color: #a9c2c8;
      font-size: .81rem;
      line-height: 1.55;
    }
    .ar-transparency {
      display: flex;
      align-items: flex-start;
      gap: .85rem;
      margin-top: 1.4rem;
      padding: 1rem 1.1rem;
      border: 1px solid rgba(66, 224, 193, .20);
      border-radius: 14px;
      background: rgba(66, 224, 193, .055);
    }
    .ar-transparency-icon {
      flex: 0 0 auto;
      color: #66e9d1;
      margin-top: .1rem;
    }
    .ar-transparency strong {
      display: block;
      color: #e5fff9;
      font-size: .88rem;
    }
    .ar-transparency p {
      margin: .25rem 0 0;
      color: #a9c7cd;
      font-size: .81rem;
      line-height: 1.6;
    }

    /* ---------- Workspace navigation ---------- */
    [class*="st-key-ar-nav-"] {
      height: 100%;
      padding: 1.25rem 1.2rem 1rem;
      border: 1px solid var(--ar-border);
      border-radius: 20px;
      background:
        radial-gradient(ellipse at 100% 0%, rgba(66, 224, 193, .07), transparent 14rem),
        linear-gradient(155deg, rgba(15, 48, 66, .82), rgba(8, 29, 43, .92));
      box-shadow: 0 16px 40px rgba(0, 0, 0, .18);
      transition: transform .2s var(--ar-ease), border-color .2s var(--ar-ease), box-shadow .2s var(--ar-ease);
    }
    [class*="st-key-ar-nav-"]:hover {
      transform: translateY(-2px);
      border-color: rgba(66, 224, 193, .34);
      box-shadow: 0 22px 50px rgba(0, 0, 0, .24);
    }
    .ar-nav-head {
      display: flex;
      align-items: center;
      gap: .75rem;
      margin-bottom: .6rem;
    }
    .ar-nav-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex: 0 0 auto;
      width: 42px;
      height: 42px;
      border: 1px solid rgba(66, 224, 193, .22);
      border-radius: 12px;
      background: rgba(66, 224, 193, .09);
      color: #72efd8;
    }
    .ar-nav-count {
      display: block;
      color: #88a9b0;
      font-size: .62rem;
      font-weight: 800;
      letter-spacing: .16em;
      text-transform: uppercase;
    }
    .ar-nav-head h3 {
      margin: .12rem 0 0 !important;
      color: #f2ffff !important;
      font-size: 1.06rem !important;
      letter-spacing: -.02em !important;
    }
    .ar-nav-copy {
      margin: 0 0 .55rem;
      color: #a6c0c6;
      font-size: .8rem;
      line-height: 1.55;
    }
    [class*="st-key-ar-nav-"] [data-testid="stPageLink"] a {
      justify-content: flex-start;
      color: #d8eef0 !important;
      font-size: .86rem;
    }
    [class*="st-key-ar-nav-"] [data-testid="stPageLink"] a:hover {
      background: rgba(66, 224, 193, .09);
      color: #8cf3df !important;
    }

    /* ---------- Footer ---------- */
    .ar-footer {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      justify-content: space-between;
      gap: 1rem 2rem;
      margin-top: clamp(3rem, 5vw, 4.5rem);
      padding-top: 1.3rem;
      border-top: 1px solid var(--ar-border);
      color: #89a5ac;
      font-size: .76rem;
      line-height: 1.6;
    }
    .ar-footer strong {
      display: block;
      color: #e7f5f5;
      font-size: .86rem;
      letter-spacing: .02em;
    }
    .ar-footer .ar-foot-right { text-align: right; }

    /* ---------- Responsive ---------- */
    @media (max-width: 1050px) {
      .ar-gallery { grid-template-columns: repeat(2, minmax(0, 1fr)); grid-auto-rows: 200px; }
      .ar-t-backwaters { grid-column: span 2; grid-row: span 2; }
      .ar-t-ghats { grid-column: span 2; }
      .ar-t-forest, .ar-t-city { grid-column: span 1; }
      .ar-hazards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .ar-flow { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 760px) {
      .ar-cine-hero {
        min-height: 560px;
        padding-bottom: clamp(2rem, 6vw, 3rem);
        border-radius: 20px;
      }
      .ar-cine-inner { padding-top: 1.2rem; }
      .ar-cine-coord { display: none; }
      .ar-cine-foot { display: none; }
      .st-key-ar-hero-ctas {
        margin-top: .7rem;
        padding: 0;
      }
      .ar-cta-note { min-height: 0; margin-top: .35rem; }
      .ar-signal { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .ar-signal > div { border-left: 0; padding: .9rem .9rem .95rem 0; }
      .ar-signal > div:nth-child(odd) { border-right: 1px solid rgba(130, 190, 199, .14); padding-right: 1rem; }
      .ar-signal > div:nth-child(n + 3) { border-top: 1px solid rgba(130, 190, 199, .14); }
      .ar-footer .ar-foot-right { text-align: left; }
    }
    @media (max-width: 600px) {
      .ar-cine-title { font-size: clamp(2.5rem, 12.4vw, 3.4rem) !important; }
      .ar-cine-title span { display: block; }
      /* Keep the phone experience calm and light on battery: one still frame. */
      .ar-cine-slide { animation: none !important; opacity: 0; }
      .ar-slide-a { opacity: 1; }
      .ar-gallery { grid-template-columns: 1fr; grid-auto-rows: 225px; }
      .ar-t-backwaters, .ar-t-ghats, .ar-t-forest, .ar-t-city { grid-column: span 1; grid-row: span 1; }
      .ar-hazards, .ar-flow { grid-template-columns: 1fr; }
      .ar-threat, .ar-why { border-radius: 20px; }
      .ar-tile figcaption { padding: .85rem .9rem; }
    }
    @media (prefers-reduced-motion: reduce) {
      .ar-cine-slide { animation: none !important; opacity: 0; transform: none !important; }
      .ar-slide-a { opacity: 1; }
      .ar-cine-video { display: none !important; }
      .ar-live-dot { animation: none !important; }
      .ar-cine-title, .ar-cine-sub, .ar-cine-desc, .ar-cine-chips { animation: none !important; }
      .ar-tile:hover img { transform: none; }
      .ar-hazard:hover, .ar-flow-step:hover,
      [class*="st-key-ar-nav-"]:hover { transform: none; }
    }
    @media (forced-colors: active) {
      /* Keep the gradient headline visible when the OS forces a palette. */
      .ar-cine-title span {
        background: none !important;
        -webkit-text-fill-color: currentColor !important;
        color: CanvasText !important;
      }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <section class="ar-cine-hero" aria-label="AI RESILIENCE - Kerala environmental and disaster intelligence">
      <div class="ar-cine-media" aria-hidden="true">
        <img class="ar-cine-poster ar-cine-slide ar-slide-a" src="{_img('hero-kerala-fallback.jpg')}"
             alt="" fetchpriority="high" decoding="async">
        <img class="ar-cine-slide ar-slide-b" src="{_img('hero-kerala-ghats.jpg')}"
             alt="" decoding="async">
        <img class="ar-cine-slide ar-slide-c" src="{_img('hero-kerala-landslide.jpg')}"
             alt="" decoding="async">
        <img class="ar-cine-slide ar-slide-d" src="{_img('hero-kerala-coast.jpg')}"
             alt="" decoding="async">{VIDEO_MARKUP}
        <span class="ar-cine-scrim"></span>
        <span class="ar-cine-vignette"></span>
        <span class="ar-cine-grain"></span>
      </div>
      <div class="ar-cine-inner">
        <div class="ar-cine-topline">
          <div class="ar-cine-kicker"><span class="ar-live-dot"></span>Kerala · Environmental &amp; disaster intelligence</div>
          <div class="ar-cine-coord">9.9312° N · 76.2673° E · Kochi</div>
        </div>
        <h1 class="ar-cine-title">AI <span>RESILIENCE</span></h1>
        <p class="ar-cine-sub">Protecting Kerala. Predicting Risks. Building a Resilient Future.</p>
        <p class="ar-cine-desc">
          One evidence-first platform for disaster intelligence, environmental monitoring,
          hospital resilience and smart mitigation — turning complex risk into clearer
          preparedness decisions for Kerala's people, landscapes and cities.
        </p>
        <div class="ar-cine-chips">
          <span>Disaster intelligence</span>
          <span>Environmental monitoring</span>
          <span>Hospital resilience</span>
          <span>Smart mitigation</span>
        </div>
      </div>
      <div class="ar-cine-foot" aria-hidden="true">
        <span>Scroll to explore</span>
        <span class="ar-scroll-line"></span>
        <span class="ar-foot-right">Beauty · Threats · Intelligence</span>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.container(key="ar-hero-ctas"):
    cta_primary, cta_secondary, cta_note = st.columns([1.05, 1.28, 1.55], gap="small")
    with cta_primary:
        if st.button(
            "Explore Intelligence",
            type="primary",
            width="stretch",
            key="home_explore_intelligence",
        ):
            st.switch_page("app_pages/decision_workflow.py")
    with cta_secondary:
        if st.button(
            "Explore Kerala's Risks",
            type="secondary",
            width="stretch",
            key="home_explore_risks",
        ):
            st.switch_page("app_pages/kochi_map.py")
    with cta_note:
        st.markdown(
            '<div class="ar-cta-note"><span><strong>Start with the evidence.</strong> '
            "Every workspace shows its sources, coverage and uncertainty.</span></div>",
            unsafe_allow_html=True,
        )

st.markdown(
    """
    <div class="ar-signal">
      <div><strong>14</strong><span>districts</span><p>A state-scale view, from the coast to the high ranges.</p></div>
      <div><strong>10</strong><span>hazard families</span><p>Flood, cyclone, landslide, heat, drought, industrial and more.</p></div>
      <div><strong>11</strong><span>workspaces</span><p>From evidence review to scenario design and mitigation planning.</p></div>
      <div><strong>Open</strong><span>by design</span><p>Methods, provenance and limitations stay visible with every result.</p></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 01 - Beauty
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="ar-story">
      <span class="ar-overline">01 · The beauty of Kerala</span>
      <h2>Landscapes that hold a civilisation.</h2>
      <p>
        Kerala is a narrow ribbon of water, forest and coast. Its backwaters carry food and
        memory; the Western Ghats shape its weather and hold its biodiversity; its beaches and
        cities are home to millions. This is the landscape the platform is built to understand
        and protect.
      </p>
    </div>
    <div class="ar-gallery">
      <figure class="ar-tile ar-t-backwaters">
        <img src="app/static/images/beauty-backwaters.webp" alt="Houseboats and palm-lined canals in the Kerala backwaters" loading="lazy" decoding="async">
        <span class="ar-tile-tag">Backwaters</span>
        <figcaption><strong>Water as a way of life</strong><span>Vembanad and the canal networks that connect village, paddy and city.</span></figcaption>
      </figure>
      <figure class="ar-tile ar-t-ghats">
        <img src="app/static/images/beauty-ghats.webp" alt="Tea plantations across the high ranges near Munnar" loading="lazy" decoding="async">
        <span class="ar-tile-tag">High ranges</span>
        <figcaption><strong>The Western Ghats</strong><span>Cloud-fed tea country and one of the world's great biodiversity hotspots.</span></figcaption>
      </figure>
      <figure class="ar-tile ar-t-waterfall">
        <img src="app/static/images/beauty-waterfall.webp" alt="Athirappilly waterfall surrounded by forest" loading="lazy" decoding="async">
        <span class="ar-tile-tag">Rivers</span>
        <figcaption><strong>Athirappilly</strong><span>Where the Chalakudy river drops through the forest edge.</span></figcaption>
      </figure>
      <figure class="ar-tile ar-t-coast">
        <img src="app/static/images/beauty-coast.webp" alt="Cliffs and beach on the Kerala coast at Varkala" loading="lazy" decoding="async">
        <span class="ar-tile-tag">Coast</span>
        <figcaption><strong>The Arabian Sea</strong><span>Cliffs, beaches and coastal communities shaped by the monsoon.</span></figcaption>
      </figure>
      <figure class="ar-tile ar-t-forest">
        <img src="app/static/images/beauty-forest.webp" alt="Shola forest and grassland in Silent Valley National Park" loading="lazy" decoding="async">
        <span class="ar-tile-tag">Biodiversity</span>
        <figcaption><strong>Silent Valley</strong><span>Shola forest, grassland and species found nowhere else on Earth.</span></figcaption>
      </figure>
      <figure class="ar-tile ar-t-city">
        <img src="app/static/images/beauty-city.webp" alt="Kochi waterfront skyline and Marine Drive" loading="lazy" decoding="async">
        <span class="ar-tile-tag">Cities</span>
        <figcaption><strong>Kochi</strong><span>A waterfront city of neighbourhoods, ports and shared infrastructure.</span></figcaption>
      </figure>
    </div>
    <p class="ar-fineprint">
      Illustrative photography from Kerala, used to celebrate the landscape and its contexts.
      Images are not evidence of current conditions or of a specific event.
    </p>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 02 - Threats
# ---------------------------------------------------------------------------
st.markdown(
    """
    <section class="ar-threat" aria-labelledby="ar-threat-title">
      <img class="ar-threat-bg" src="app/static/images/threats-monsoon.webp"
           alt="" loading="lazy" decoding="async" aria-hidden="true">
      <span class="ar-threat-scrim"></span>
      <div class="ar-threat-inner">
        <div class="ar-story">
          <span class="ar-overline">02 · The threats we face</span>
          <h2 id="ar-threat-title">Beauty under pressure.</h2>
          <p>
            The same water, slopes and coastlines that make Kerala extraordinary also carry
            risk. A changing climate and growing urban footprint are testing the systems that
            keep communities safe. The platform treats these hazards as connected, not isolated.
          </p>
        </div>
        <div class="ar-hazards">
          <article class="ar-hazard">
            <span class="ar-hazard-icon">__FLOOD__</span>
            <h3>Floods &amp; urban waterlogging</h3>
            <p>Monsoon surges and drainage failure can overwhelm neighbourhoods, roads and essential services.</p>
          </article>
          <article class="ar-hazard">
            <span class="ar-hazard-icon">__LANDSLIDE__</span>
            <h3>Landslides</h3>
            <p>Steep, rain-soaked slopes in the Western Ghats put settlements, hill roads and livelihoods at risk.</p>
          </article>
          <article class="ar-hazard">
            <span class="ar-hazard-icon">__CYCLONE__</span>
            <h3>Cyclones &amp; coastal hazards</h3>
            <p>Storm surge, wind and coastal erosion threaten lives, homes and critical infrastructure.</p>
          </article>
          <article class="ar-hazard">
            <span class="ar-hazard-icon">__FACTORY__</span>
            <h3>Air &amp; industrial pollution</h3>
            <p>Industrial corridors and urban emissions affect air quality, public health and the wider environment.</p>
          </article>
          <article class="ar-hazard">
            <span class="ar-hazard-icon">__RAIN__</span>
            <h3>Extreme rainfall</h3>
            <p>Shorter, more intense spells stress rivers, reservoirs, soils and drainage systems.</p>
          </article>
          <article class="ar-hazard">
            <span class="ar-hazard-icon">__LEAF__</span>
            <h3>Environmental degradation</h3>
            <p>Loss of wetlands, forests and natural buffers reduces the landscape's capacity to absorb shocks.</p>
          </article>
        </div>
        <p class="ar-fineprint">
          Atmospheric context imagery, not a photograph of a specific disaster event. Hazard
          statements are general context; any site-specific conclusion must be supported by the
          data and validation shown in the relevant workspace.
        </p>
      </div>
    </section>
    """.replace("__FLOOD__", ICON_FLOOD)
    .replace("__LANDSLIDE__", ICON_LANDSLIDE)
    .replace("__CYCLONE__", ICON_CYCLONE)
    .replace("__FACTORY__", ICON_FACTORY)
    .replace("__RAIN__", ICON_RAIN)
    .replace("__LEAF__", ICON_LEAF),
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 03 - Why it matters
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <section class="ar-why" aria-labelledby="ar-why-title">
      <div class="ar-story" style="margin-top:0">
        <span class="ar-overline">03 · Why AI_RESILIENCE matters</span>
        <h2 id="ar-why-title">From observation to action, in one evidence chain.</h2>
        <p>
          Preparedness improves when monitoring, risk assessment, critical-facility intelligence
          and mitigation planning speak the same language. AI_RESILIENCE connects those steps
          without hiding the uncertainty between them.
        </p>
      </div>
      <ol class="ar-flow">
        <li class="ar-flow-step">
          <span class="ar-step-no">01 · Monitor</span>
          <h3>See the environment</h3>
          <p>Bring rainfall, hydrology, air quality and spatial context into a shared view of what is changing.</p>
        </li>
        <li class="ar-flow-step">
          <span class="ar-step-no">02 · Assess</span>
          <h3>Understand the risk</h3>
          <p>Explore multi-hazard scenarios with explicit assumptions, evidence quality and uncertainty.</p>
        </li>
        <li class="ar-flow-step">
          <span class="ar-step-no">03 · Protect</span>
          <h3>Guard critical care</h3>
          <p>Examine hospital exposure and continuity questions before an emergency tests them.</p>
        </li>
        <li class="ar-flow-step">
          <span class="ar-step-no">04 · Prepare</span>
          <h3>Plan smart mitigation</h3>
          <p>Compare interventions, structure concept designs and check the arithmetic behind budgets.</p>
        </li>
      </ol>
      <div class="ar-transparency">
        <span class="ar-transparency-icon">{ICON_SHIELD}</span>
        <div>
          <strong>Evidence-first, not certainty-first.</strong>
          <p>
            This is a research prototype, not an official warning service. Scenario outputs are
            not automatically validated probabilities, and historical observations do not prove
            current conditions or identify a pollution source. In an emergency, follow the Kerala
            State Disaster Management Authority, IMD and district-administration guidance.
          </p>
        </div>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 04 - Explore the workspaces
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="ar-story">
      <span class="ar-overline">04 · Explore the intelligence platform</span>
      <h2>Choose a workspace.</h2>
      <p>
        Move from understanding the landscape to examining a specific question. Every module is
        part of the same evidence-first system, and every result should be read alongside its
        source, coverage and validation status.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

navigation_groups = [
    (
        "ar-nav-risk",
        ICON_COMPASS,
        "Risk & readiness",
        "Build a scenario, inspect the evidence and understand what the models can — and cannot — tell you.",
        [
            ("app_pages/decision_workflow.py", "Decision Workflow", ":material/assignment_turned_in:"),
            ("app_pages/disaster_probability.py", "Ernakulam Risk Assessment", ":material/analytics:"),
            ("app_pages/compound_scenario.py", "Cyclone + Flood", ":material/thunderstorm:"),
        ],
    ),
    (
        "ar-nav-place",
        ICON_PLACE,
        "Place & environment",
        "See the geography, monitor environmental pressure and test whether the underlying data is fit for use.",
        [
            ("app_pages/kochi_map.py", "Kochi Map", ":material/map:"),
            ("app_pages/air_pollution.py", "Air Pollution", ":material/factory:"),
            ("app_pages/data_readiness.py", "Data Readiness", ":material/fact_check:"),
        ],
    ),
    (
        "ar-nav-people",
        ICON_HOSPITAL,
        "People & critical services",
        "Bring exposure, continuity and preparedness questions closer to the facilities communities rely on.",
        [
            ("app_pages/hospital_vulnerability.py", "Hospital Vulnerability", ":material/local_hospital:"),
            ("app_pages/disaster_assistant.py", "Disaster Intelligence Assistant", ":material/psychology_alt:"),
            ("app_pages/hazard_model_lab.py", "Hazard Model Lab", ":material/model_training:"),
        ],
    ),
    (
        "ar-nav-plan",
        ICON_BLUEPRINT,
        "Plan & design",
        "Turn priorities into transparent mitigation options, concept designs and budget checks.",
        [
            ("app_pages/mitigation_planner.py", "Mitigation Budget", ":material/account_balance_wallet:"),
            ("app_pages/smart_mitigation_design.py", "Smart Mitigation Design", ":material/engineering:"),
        ],
    ),
]

for row_start in range(0, len(navigation_groups), 2):
    columns = st.columns(2, gap="medium")
    for column, group in zip(columns, navigation_groups[row_start:row_start + 2]):
        key, icon, title, copy, links = group
        with column:
            with st.container(key=key):
                st.markdown(
                    f"""
                    <div class="ar-nav-head">
                      <span class="ar-nav-icon">{icon}</span>
                      <div>
                        <span class="ar-nav-count">{len(links)} workspace{"s" if len(links) != 1 else ""}</span>
                        <h3>{title}</h3>
                      </div>
                    </div>
                    <p class="ar-nav-copy">{copy}</p>
                    """,
                    unsafe_allow_html=True,
                )
                for path, label, page_icon in links:
                    st.page_link(path, label=label, icon=page_icon, width="stretch")

# ---------------------------------------------------------------------------
# Footer and credits
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="ar-footer">
      <div>
        <strong>AI RESILIENCE</strong>
        Kerala environmental &amp; disaster intelligence · Evidence-first, human-centred.
      </div>
      <div class="ar-foot-right">
        Built around open, documented data sources.<br>
        SDG 11 · Sustainable cities and communities &nbsp;|&nbsp; SDG 13 · Climate action
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Photography credits and licensing", expanded=False):
    st.markdown(
        """
        Landscape photography is used for illustrative context only and is not presented as
        evidence of a specific event or current condition. Images were cropped, resized and
        colour-balanced for this interface.

        - **Flooded NH544, Companypady (hero fallback)** — Dil Shad Roshan,
          [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0),
          [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Flooded-nh544-companypady-2018-kerala-floods.jpg).
        - **Monsoon over the Western Ghats (hero)** — Planemad,
          [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/),
          [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Monsoon_view_of_the_Sengottai_Gap_in_the_Western_Ghats.jpg).
        - **Wayanad landslide aftermath (hero)** — Vis M,
          [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0),
          [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Wayanad_landslides_aftermath.jpg).
        - **Kerala coast before heavy rain (hero)** — Midhundas1010,
          [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0),
          [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:The_sea_before_rain.jpg).
        - **Kerala backwaters** — Thursdaynext,
          [CC BY 2.0](https://creativecommons.org/licenses/by/2.0),
          [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Kerala_backwater_scene.jpg).
        - **Munnar tea plantations** — Ingo Mehling,
          [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0),
          [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Munnar_-_Lockhart_tea_plantation.jpg).
        - **Athirappilly Falls** — Vis M, [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/),
          [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Athirappilly_Falls_2024.jpg).
        - **Varkala coast** — BinoBose,
          [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0),
          [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Varkala_Beach_01.jpg).
        - **Silent Valley forest** — Davidvraju, [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/),
          [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Shola_Forest_Silent_valley_NP_(2).jpg).
        - **Kochi waterfront** — Galib Tufan,
          [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0),
          [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Marine_Drive_skyline_with_High_Court_Water_Metro_Terminal_Kochi_2026-09-06_05491.jpg).
        - **Monsoon clouds** — Nagesh Jayaraman,
          [CC BY 2.0](https://creativecommons.org/licenses/by/2.0),
          [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Kerala_Monsoon_clouds_over_Western_Ghats_India.jpg).
        """
    )
