"""Kochi-focused environmental and disaster-intelligence homepage for AI RESILIENCE.

The page introduces Kochi's urban resilience context, explains the evidence-first
workflow, and routes users into the existing analytical workspaces. Regional
photography is illustrative context; analytical scope remains Kochi-focused.

Hero film
---------
Drop your own footage at ``assets/videos/kerala_hero.mp4``. On the next rerun
the file is made available through Streamlit's static file route and used as a
muted, looping, cover-fit background. Until then - or if the file is removed -
the optimised local photograph in ``static/images/`` is shown instead. No
remote video URL and no placeholder video file is referenced.
"""

from pathlib import Path
import html
import shutil

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
STATIC_IMAGES = "app/static/images"
ASSETS_VIDEO = ROOT / "assets" / "videos" / "kerala_hero.mp4"
STATIC_VIDEO = ROOT / "static" / "videos" / "kerala_hero.mp4"
STATIC_VIDEO_URL = "app/static/videos/kerala_hero.mp4"



def _workspace_link(path: str, label: str, page_icon: str = "") -> None:
    """Render a stable URL link to a page registered by app.py."""
    route = Path(path).stem
    safe_label = html.escape(label)
    st.markdown(
        f'<a class="ar-workspace-link" href="/{route}">'
        f'<span class="ar-workspace-link-label">{safe_label}</span>'
        f'<span class="ar-workspace-link-action">Open workspace <span aria-hidden="true">&#8594;</span></span>'
        f'</a>',
        unsafe_allow_html=True,
    )

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
      animation: arSlideCycle 64s cubic-bezier(.45, .05, .55, .95) infinite;
      will-change: opacity, transform;
    }
    .ar-cine-hero .ar-slide-a { object-position: center 56%; animation-delay: 0s; }
    .ar-cine-hero .ar-slide-b { object-position: center 46%; animation-delay: -8s; }
    .ar-cine-hero .ar-slide-c { object-position: center 52%; animation-delay: -16s; }
    .ar-cine-hero .ar-slide-d { object-position: center 50%; animation-delay: -24s; }
    .ar-cine-hero .ar-slide-e { object-position: center 50%; animation-delay: -32s; }
    .ar-cine-hero .ar-slide-f { object-position: center 50%; animation-delay: -40s; }
    .ar-cine-hero .ar-slide-g { object-position: center 50%; animation-delay: -48s; }
    .ar-cine-hero .ar-slide-h { object-position: center 50%; animation-delay: -56s; }
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
    .ar-nav-media {
      min-height: 106px;
      margin: -.25rem -.25rem 1rem;
      border-radius: 14px;
      background-position: center;
      background-size: cover;
      box-shadow: inset 0 -22px 28px rgba(7, 30, 27, .16);
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

    /* ---------- Subtle scroll-linked parallax ---------- */
    /*
       Progressive enhancement: browsers with CSS scroll-driven animations get
       gentle depth while scrolling. Older browsers keep the existing layout.
       No JavaScript listeners, fake map data or extra network requests.
    */
    @keyframes arHeroParallax {
      from { transform: translate3d(0, 0, 0) scale(1); }
      to   { transform: translate3d(0, 7%, 0) scale(1.08); }
    }
    @keyframes arThreatParallax {
      from { transform: translate3d(0, -4%, 0) scale(1.08); }
      to   { transform: translate3d(0, 4%, 0) scale(1.08); }
    }
    @supports (animation-timeline: view()) {
      .ar-cine-hero {
        view-timeline-name: --ar-hero-view;
        view-timeline-axis: block;
      }
      .ar-cine-media {
        animation: arHeroParallax 1s linear both;
        animation-timeline: --ar-hero-view;
        animation-range: exit 0% exit 100%;
        will-change: transform;
      }
      .ar-threat {
        view-timeline-name: --ar-threat-view;
        view-timeline-axis: block;
      }
      .ar-threat .ar-threat-bg {
        animation: arThreatParallax 1s linear both;
        animation-timeline: --ar-threat-view;
        animation-range: entry 0% exit 100%;
        will-change: transform;
      }
    }

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
      .ar-nav-media { min-height: 88px; }
    }
    @media (prefers-reduced-motion: reduce) {
      .ar-cine-slide { animation: none !important; opacity: 0; transform: none !important; }
      .ar-cine-media, .ar-threat .ar-threat-bg { animation: none !important; transform: none !important; }
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
    <section class="ar-cine-hero" aria-label="AI RESILIENCE - Kochi environmental and disaster intelligence">
      <div class="ar-cine-media" aria-hidden="true">
        <img class="ar-cine-poster ar-cine-slide ar-slide-a" src="{_img('kochi/waterfront.jpg')}"
             alt="" fetchpriority="high" decoding="async">
        <img class="ar-cine-slide ar-slide-b" src="{_img('kochi/backwaters.jpg')}"
             alt="" decoding="async">
        <img class="ar-cine-slide ar-slide-c" src="{_img('kochi/mangalavanam.jpg')}"
             alt="" decoding="async">
        <img class="ar-cine-slide ar-slide-d" src="{_img('kochi/fishing-nets.jpg')}"
             alt="" decoding="async">
        <img class="ar-cine-slide ar-slide-e" src="{_img('kochi/coast.jpg')}"
             alt="" decoding="async">
        <img class="ar-cine-slide ar-slide-f" src="{_img('kochi/industrial-coast.jpg')}"
             alt="" decoding="async">
        <img class="ar-cine-slide ar-slide-g" src="{_img('kochi/maradu.jpg')}"
             alt="" decoding="async">
        <img class="ar-cine-slide ar-slide-h" src="{_img('kochi/water-metro.jpg')}"
             alt="" decoding="async">{VIDEO_MARKUP}
        <span class="ar-cine-scrim"></span>
        <span class="ar-cine-vignette"></span>
        <span class="ar-cine-grain"></span>
      </div>
      <div class="ar-cine-inner">
        <div class="ar-cine-topline">
          <div class="ar-cine-kicker"><span class="ar-scope-dot" aria-hidden="true"></span>Kochi · Environmental &amp; disaster intelligence</div>
          <div class="ar-cine-coord">9.9312° N · 76.2673° E · Kochi</div>
        </div>
        <h1 class="ar-cine-title">AI <span>RESILIENCE</span></h1>
        <p class="ar-cine-sub">Understanding Kochi. Preparing for risk. Strengthening urban resilience.</p>
        <p class="ar-cine-desc">
          A Kochi-focused, evidence-first platform for environmental monitoring, multi-hazard
          review, critical-service resilience and mitigation planning. Explore documented
          data, understand uncertainty and support better-informed local decisions.
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
        <span class="ar-foot-right">Assess · Map · Prepare</span>
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
            "Explore Kochi's Risk Context",
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

st.warning(
    "RESEARCH-GRADE SCREENING · AI_RESILIENCE is an evidence-gated research "
    "demonstration and decision-support platform, not an operational early-warning "
    "service. It does not claim validated Kochi flood probabilities, predicted "
    "inundation depths, verified affected-population counts, or proven intervention "
    "benefits. Follow official IMD, CWC, KSDMA and local-authority instructions "
    "for real safety decisions."
)

st.markdown(
    """
    <div class="ar-signal" aria-label="Platform principles and scope">
      <div><strong>Kochi</strong><span>pilot geography</span><p>City-focused spatial and environmental intelligence.</p></div>
      <div><strong>Evidence</strong><span>first approach</span><p>Source coverage, provenance and uncertainty stay visible.</p></div>
      <div><strong>11</strong><span>workspaces</span><p>Monitoring, risk review, critical services and mitigation planning.</p></div>
      <div><strong>Human</strong><span>led decisions</span><p>Research support — not an official warning or emergency service.</p></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Priority decision panel — primary user tasks appear before background content.
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .ar-priority-intro { margin: 2.2rem 0 1rem; max-width: 900px; }
    .ar-priority-kicker {
      color: #247a65; font-size: .7rem; font-weight: 850;
      letter-spacing: .16em; text-transform: uppercase;
    }
    .ar-priority-intro h2 {
      margin: .45rem 0 .5rem; color: #173f39; font-size: clamp(1.8rem,3.2vw,2.7rem);
      line-height: 1.08; letter-spacing: -.04em;
    }
    .ar-priority-intro p { margin: 0; max-width: 760px; color: #5d7068; line-height: 1.65; }
    .ar-priority-card {
      height: 100%; min-height: 190px; padding: 1.15rem 1.2rem;
      border: 1px solid rgba(36,122,101,.20); border-radius: 18px;
      background: linear-gradient(150deg,rgba(255,255,255,.98),rgba(235,246,239,.94));
      box-shadow: 0 12px 30px rgba(26,65,49,.065);
    }
    .ar-priority-card .ar-priority-index {
      display:inline-flex; align-items:center; justify-content:center;
      width:2rem; height:2rem; border-radius:10px; margin-bottom:.8rem;
      color:#176b54; background:rgba(36,122,101,.10); font-weight:850; font-size:.78rem;
    }
    .ar-priority-card h3 { margin:0 0 .45rem; color:#23473b; font-size:1.08rem; letter-spacing:-.02em; }
    .ar-priority-card p { min-height:3.6rem; margin:0 0 .85rem; color:#63766e; font-size:.84rem; line-height:1.55; }
    [class*="st-key-ar-priority-"] [data-testid="stPageLink"] a {
      width:100%; justify-content:space-between; border-radius:10px;
      border:1px solid rgba(36,122,101,.20); background:rgba(36,122,101,.07);
      color:#176b54 !important; font-weight:750; padding:.62rem .75rem;
    }
    [class*="st-key-ar-priority-"] [data-testid="stPageLink"] a:hover {
      background:rgba(36,122,101,.13); border-color:rgba(36,122,101,.38);
    }
    .ar-priority-note {
      margin:.9rem 0 0; padding:.75rem .9rem; border-left:3px solid #b98a42;
      border-radius:0 10px 10px 0; background:rgba(248,243,231,.82);
      color:#6f5a35; font-size:.78rem; line-height:1.55;
    }
    @media(max-width:700px) {
      .ar-priority-card { min-height:0; }
      .ar-priority-card p { min-height:0; }
    }
    </style>
    <section class="ar-priority-intro" aria-labelledby="ar-priority-title">
      <span class="ar-priority-kicker">Start here · Priority intelligence</span>
      <h2 id="ar-priority-title">Assess first. See the place. Plan the response.</h2>
      <p>Open the three core workspaces first. Review a disaster scenario and its precautions, inspect Kochi's available spatial evidence, or examine what the research models can genuinely support.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

priority_columns = st.columns(3, gap="medium")
priority_cards = [
    (
        "01",
        "Scenario assessment & precautions",
        "Select a hazard or compound event, review evidence and uncertainty, and identify practical preparedness and mitigation priorities.",
        "app_pages/decision_workflow.py",
        "Open decision workflow",
    ),
    (
        "02",
        "Kochi interactive map",
        "Explore the available Kochi boundary and source-documented spatial layers, with the map's own legend and data-quality notes.",
        "app_pages/kochi_map.py",
        "Explore Kochi map",
    ),
    (
        "03",
        "Prediction & ML evidence",
        "Inspect trained research models, held-out comparisons, inference readiness and the limits that prevent unsupported warnings.",
        "app_pages/submission_ml_demo.py",
        "Review ML evidence",
    ),
]
for column, (number, title, description, path, link_label) in zip(priority_columns, priority_cards):
    with column:
        with st.container(key=f"ar-priority-{number}"):
            st.markdown(
                f'<div class="ar-priority-card"><span class="ar-priority-index">{number}</span>'
                f'<h3>{title}</h3><p>{description}</p></div>',
                unsafe_allow_html=True,
            )
            _workspace_link(path, link_label)

st.markdown(
    '<div class="ar-priority-note"><strong>Prediction integrity:</strong> '
    'The platform presents numerical estimates only where a registered model and complete input context are available. '
    'Research outputs are not official forecasts or public warnings; follow IMD, KSDMA and district-administration guidance.</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 01 - Kochi in focus
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="ar-story">
      <span class="ar-overline">02 · Kochi in focus</span>
      <h2>Beauty, biodiversity and a city shaped by water.</h2>
      <p>
        Kochi is a living network of islands, backwaters, mangroves, fishing communities and
        working waterfronts. Its beauty and vulnerability are connected: the same waterways
        that sustain the city can carry floodwater, pollution and pressure on coastal ecosystems.
      </p>
    </div>
    <div class="ar-gallery">
      <figure class="ar-tile ar-t-backwaters">
        <img src="app/static/images/kochi/backwaters.jpg" alt="Kochi backwaters and palm-lined waterways" loading="lazy" decoding="async">
        <span class="ar-tile-tag">Backwaters</span>
        <figcaption><strong>Water as a way of life</strong><span>Backwaters and canals connect neighbourhoods, livelihoods and ecosystems.</span></figcaption>
      </figure>
      <figure class="ar-tile ar-t-ghats">
        <img src="app/static/images/kochi/fishing-nets.jpg" alt="Chinese fishing nets on the Kochi waterfront" loading="lazy" decoding="async">
        <span class="ar-tile-tag">Fort Kochi</span>
        <figcaption><strong>Working waterfronts</strong><span>Fishing heritage, tidal water and livelihoods meet at the city edge.</span></figcaption>
      </figure>
      <figure class="ar-tile ar-t-waterfall">
        <img src="app/static/images/kochi/mangalavanam.jpg" alt="Green wetland vegetation at Mangalavanam in Kochi" loading="lazy" decoding="async">
        <span class="ar-tile-tag">Urban ecology</span>
        <figcaption><strong>Green breathing spaces</strong><span>Mangalavanam and urban wetlands shelter biodiversity inside a growing city.</span></figcaption>
      </figure>
      <figure class="ar-tile ar-t-coast">
        <img src="app/static/images/kochi/coast.jpg" alt="Kochi coastline and Arabian Sea" loading="lazy" decoding="async">
        <span class="ar-tile-tag">Coastline</span>
        <figcaption><strong>Where land meets sea</strong><span>Coastal communities face erosion, storms and changing shoreline pressures.</span></figcaption>
      </figure>
      <figure class="ar-tile ar-t-forest">
        <img src="app/static/images/kochi/waterfront.jpg" alt="Kochi waterfront with water and urban greenery" loading="lazy" decoding="async">
        <span class="ar-tile-tag">City &amp; water</span>
        <figcaption><strong>One connected landscape</strong><span>Ports, homes, roads and waterways share the same environmental systems.</span></figcaption>
      </figure>
      <figure class="ar-tile ar-t-city">
        <img src="app/static/images/kochi/industrial-coast.jpg" alt="Industrial waterfront surroundings near Kochi" loading="lazy" decoding="async">
        <span class="ar-tile-tag">Pressure points</span>
        <figcaption><strong>Growth needs care</strong><span>Industry and infrastructure must grow alongside clean air, water and public health.</span></figcaption>
      </figure>
    </div>
    <p class="ar-fineprint">
      Kochi photography provides visual context only. Images are not evidence of current
      conditions or a specific event; use the linked workspaces for documented data and sources.
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
      <img class="ar-threat-bg" src="app/static/images/kochi/industrial-coast.jpg"
           alt="" loading="lazy" decoding="async" aria-hidden="true">
      <span class="ar-threat-scrim"></span>
      <div class="ar-threat-inner">
        <div class="ar-story">
          <span class="ar-overline">03 · The threats we face</span>
          <h2 id="ar-threat-title">Beauty under pressure.</h2>
          <p>
            Kochi's waterways, coastal setting and dense urban footprint create connected planning
            questions. Heavy rainfall, drainage constraints, coastal pressures and environmental
            change can affect neighbourhoods and essential services in different ways.
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
        <span class="ar-overline">04 · Why AI_RESILIENCE matters</span>
        <h2 id="ar-why-title">From observation to action, in one evidence chain.</h2>
        <p>
          Urban preparedness improves when environmental monitoring, hazard review, critical-facility
          context and mitigation planning speak the same language. AI RESILIENCE connects those
          steps while keeping evidence gaps and uncertainty visible.
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
            This is a Kochi-focused research prototype, not an official warning service. Scenario outputs are
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
      <span class="ar-overline">05 · Explore the intelligence platform</span>
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
        "app/static/images/kochi/coast.jpg",
        [
            ("app_pages/decision_workflow.py", "Decision Workflow", ":material/assignment_turned_in:"),
            ("app_pages/disaster_probability.py", "Multi-Hazard Evidence Review", ":material/analytics:"),
            ("app_pages/compound_scenario.py", "Cyclone + Flood", ":material/thunderstorm:"),
        ],
    ),
    (
        "ar-nav-place",
        ICON_PLACE,
        "Place & environment",
        "See the geography, monitor environmental pressure and test whether the underlying data is fit for use.",
        "app/static/images/kochi/backwaters.jpg",
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
        "app/static/images/kochi/mangalavanam.jpg",
        [
            ("app_pages/hospital_vulnerability.py", "Hospital Vulnerability", ":material/local_hospital:"),
            ("app_pages/disaster_assistant.py", "Disaster Intelligence Assistant", ":material/psychology_alt:"),
            ("app_pages/hazard_model_lab.py", "Hazard Model Lab", ":material/model_training:"),
            ("app_pages/submission_ml_demo.py", "ML Evidence & Demonstration", ":material/science:"),
        ],
    ),
    (
        "ar-nav-plan",
        ICON_BLUEPRINT,
        "Plan & design",
        "Turn priorities into transparent mitigation options, concept designs and budget checks.",
        "app/static/images/kochi/fishing-nets.jpg",
        [
            ("app_pages/mitigation_planner.py", "Mitigation Budget", ":material/account_balance_wallet:"),
            ("app_pages/smart_mitigation_design.py", "Smart Mitigation Design", ":material/engineering:"),
        ],
    ),
]

for row_start in range(0, len(navigation_groups), 2):
    columns = st.columns(2, gap="medium")
    for column, group in zip(columns, navigation_groups[row_start:row_start + 2]):
        key, icon, title, copy, image, links = group
        with column:
            with st.container(key=key):
                st.markdown(
                    f"""
                    <div class="ar-nav-media" style="background-image:linear-gradient(90deg,rgba(8,39,37,.76),rgba(8,39,37,.16)),url('{image}');" role="img" aria-label="{title} workspace environment"></div>
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
                    _workspace_link(path, label, page_icon)

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 05 - Contribution to the Sustainable Development Goals
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
.ar-sdg-section {
  position:relative; overflow:hidden; margin:clamp(3rem,5vw,4.5rem) 0 1.2rem;
  padding:clamp(1.35rem,3vw,2.6rem); border:1px solid rgba(23,78,85,.14);
  border-radius:26px; background:linear-gradient(145deg,#fff 0%,#f1f7f5 58%,#e6f0ef 100%);
  box-shadow:0 22px 56px rgba(23,78,85,.075);
}
.ar-sdg-section:before { content:""; position:absolute; width:420px;height:420px;right:-210px;top:-230px;border-radius:50%;background:radial-gradient(circle,rgba(41,155,145,.13),transparent 68%);pointer-events:none; }
.ar-sdg-kicker { color:#247f77;font-size:.7rem;font-weight:850;letter-spacing:.17em;text-transform:uppercase; }
.ar-sdg-hero { display:grid;grid-template-columns:minmax(0,1.1fr) minmax(300px,.9fr);gap:1.2rem;align-items:center; }
.ar-sdg-title { margin:.65rem 0 .8rem!important;color:#173f43!important;font-size:clamp(2rem,4vw,3.45rem)!important;line-height:1.02!important;letter-spacing:-.05em!important; }
.ar-sdg-lede { max-width:700px;color:#586f6b;font-size:1rem;line-height:1.75; }
.ar-sdg-callout { display:inline-flex;gap:.55rem;align-items:center;margin-top:.8rem;padding:.55rem .8rem;border:1px solid rgba(41,155,145,.2);border-radius:999px;background:rgba(220,231,232,.55);color:#285d59;font-size:.76rem;font-weight:700; }
.ar-sdg-network { position:relative;min-height:270px;display:grid;place-items:center; }
.ar-sdg-network svg { position:absolute;inset:0;width:100%;height:100%;overflow:visible; }
.ar-sdg-hub { z-index:1;display:grid;place-items:center;width:126px;height:126px;border:1px solid rgba(41,155,145,.3);border-radius:50%;background:linear-gradient(145deg,#fff,#e1efec);box-shadow:0 12px 35px rgba(23,78,85,.13);text-align:center;color:#174e55; }
.ar-sdg-hub strong { font-size:1rem;letter-spacing:-.03em; }
.ar-sdg-hub span { font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;color:#52716d; }
.ar-sdg-node { position:absolute;z-index:2;display:grid;place-items:center;width:56px;height:56px;border:3px solid #fff;border-radius:15px;background:#fff;box-shadow:0 8px 20px rgba(23,78,85,.15); }
.ar-sdg-node img { width:100%;height:100%;object-fit:contain;border-radius:12px; }
.ar-sdg-node.n3 {top:7%;left:18%}.ar-sdg-node.n6 {top:7%;right:18%}.ar-sdg-node.n9 {top:42%;right:3%}.ar-sdg-node.n11 {bottom:7%;right:18%}.ar-sdg-node.n13 {bottom:7%;left:18%}.ar-sdg-node.n15 {top:42%;left:3%}
.ar-sdg-section .ar-sdg-divider {height:1px;margin:1.4rem 0;background:linear-gradient(90deg,transparent,rgba(23,78,85,.18),transparent);}
.ar-sdg-subhead {display:flex;align-items:end;justify-content:space-between;gap:1rem;margin:0 0 1rem;}
.ar-sdg-subhead h3 {margin:0!important;color:#173f43!important;font-size:1.22rem!important;letter-spacing:-.025em!important;}
.ar-sdg-subhead p {margin:0;color:#71827b;font-size:.76rem;}
.ar-sdg-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.85rem;}
.ar-sdg-card {--sdg-color:#247f77;display:grid;grid-template-columns:62px minmax(0,1fr);gap:.8rem;min-height:150px;padding:1rem;border:1px solid rgba(23,78,85,.13);border-left:4px solid var(--sdg-color);border-radius:17px;background:rgba(255,255,255,.88);box-shadow:0 8px 22px rgba(23,78,85,.045);transition:transform .2s ease,box-shadow .2s ease;}
.ar-sdg-card:hover {transform:translateY(-3px);box-shadow:0 14px 28px rgba(23,78,85,.1);}
.ar-sdg-card img {width:62px;height:62px;object-fit:contain;border-radius:8px;}
.ar-sdg-card h4 {margin:.05rem 0 .35rem!important;color:#173f43!important;font-size:.92rem!important;line-height:1.25!important;}
.ar-sdg-card h4 span {display:block;margin-bottom:.2rem;color:var(--sdg-color);font-size:.65rem;font-weight:850;letter-spacing:.1em;text-transform:uppercase;}
.ar-sdg-card p {margin:0;color:#5d716d;font-size:.77rem;line-height:1.55;}
.ar-sdg-footer {display:flex;gap:.7rem;align-items:flex-start;margin-top:1rem;padding:.9rem 1rem;border:1px solid rgba(41,155,145,.18);border-radius:14px;background:rgba(220,231,232,.55);color:#536d68;font-size:.75rem;line-height:1.6;}
.ar-sdg-footer strong {color:#174e55;}
.ar-sdg-note {margin-top:.8rem;color:#71827b;font-size:.67rem;line-height:1.55;}
.ar-sdg-note a {color:#176b54!important;text-decoration:underline;text-underline-offset:2px;}
@media(max-width:900px){.ar-sdg-hero{grid-template-columns:1fr}.ar-sdg-network{min-height:230px}.ar-sdg-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){.ar-sdg-grid{grid-template-columns:1fr}.ar-sdg-card{min-height:0}.ar-sdg-network{min-height:210px}.ar-sdg-node{width:48px;height:48px}}
@media(prefers-reduced-motion:reduce){.ar-sdg-card{transition:none}.ar-sdg-card:hover{transform:none}}
</style>
<section class="ar-sdg-section" aria-labelledby="ar-sdg-title">
  <div class="ar-sdg-hero">
    <div>
      <span class="ar-sdg-kicker">06 · Shared direction · Kochi to the world</span>
      <h2 class="ar-sdg-title" id="ar-sdg-title">Local resilience. Global goals.</h2>
      <p class="ar-sdg-lede">AI RESILIENCE brings environmental evidence, disaster preparedness and infrastructure planning into one Kochi-focused workspace. Its work connects to six Sustainable Development Goals through practical research and planning capabilities.</p>
      <span class="ar-sdg-callout">Six goals · One evidence-led platform · Kochi pilot</span>
    </div>
    <div class="ar-sdg-network" role="img" aria-label="Six Sustainable Development Goal icons connected to the AI RESILIENCE platform hub">
      <svg viewBox="0 0 420 270" aria-hidden="true"><g fill="none" stroke="#75aaa2" stroke-width="1.5" stroke-dasharray="4 5" opacity=".8"><path d="M210 135 L105 38 M210 135 L315 38 M210 135 L392 135 M210 135 L315 232 M210 135 L105 232 M210 135 L28 135"/></g><g fill="#299b91"><circle cx="105" cy="38" r="3"/><circle cx="315" cy="38" r="3"/><circle cx="392" cy="135" r="3"/><circle cx="315" cy="232" r="3"/><circle cx="105" cy="232" r="3"/><circle cx="28" cy="135" r="3"/></g></svg>
      <div class="ar-sdg-hub"><div><strong>AI<br>RESILIENCE</strong><br><span>Kochi · Kerala</span></div></div>
      <div class="ar-sdg-node n3"><img src="app/static/images/sdg/sdg-3.png" alt=""></div>
      <div class="ar-sdg-node n6"><img src="app/static/images/sdg/sdg-6.png" alt=""></div>
      <div class="ar-sdg-node n9"><img src="app/static/images/sdg/sdg-9.png" alt=""></div>
      <div class="ar-sdg-node n11"><img src="app/static/images/sdg/sdg-11.png" alt=""></div>
      <div class="ar-sdg-node n13"><img src="app/static/images/sdg/sdg-13.png" alt=""></div>
      <div class="ar-sdg-node n15"><img src="app/static/images/sdg/sdg-15.png" alt=""></div>
    </div>
  </div>
  <div class="ar-sdg-divider"></div>
  <div class="ar-sdg-subhead"><h3>Six goals. Six contribution pathways.</h3><p>Explore the platform capability behind each connection.</p></div>
  <div class="ar-sdg-grid">
    <article class="ar-sdg-card" style="--sdg-color:#4c9f38"><img src="app/static/images/sdg/sdg-3.png" alt="SDG 3 official icon"><div><h4><span>Goal 03 · People</span>Good Health and Well-being</h4><p>Hospital vulnerability and preparedness work examine exposure and continuity questions for critical healthcare services.</p></div></article>
    <article class="ar-sdg-card" style="--sdg-color:#26bde2"><img src="app/static/images/sdg/sdg-6.png" alt="SDG 6 official icon"><div><h4><span>Goal 06 · Water</span>Clean Water and Sanitation</h4><p>Flood and hydrology evidence helps investigate water-related pressures, drainage context and observation gaps.</p></div></article>
    <article class="ar-sdg-card" style="--sdg-color:#f36d25"><img src="app/static/images/sdg/sdg-9.png" alt="SDG 9 official icon"><div><h4><span>Goal 09 · Infrastructure</span>Industry, Innovation and Infrastructure</h4><p>Air-quality context and mitigation planning bring documented evidence into infrastructure discussions.</p></div></article>
    <article class="ar-sdg-card" style="--sdg-color:#f99d26"><img src="app/static/images/sdg/sdg-11.png" alt="SDG 11 official icon"><div><h4><span>Goal 11 · Cities</span>Sustainable Cities and Communities</h4><p>Kochi-focused mapping, hazard evidence review and decision workflows support urban resilience planning.</p></div></article>
    <article class="ar-sdg-card" style="--sdg-color:#3f7e44"><img src="app/static/images/sdg/sdg-13.png" alt="SDG 13 official icon"><div><h4><span>Goal 13 · Climate</span>Climate Action</h4><p>Rainfall, hazard and scenario evidence help explore climate-related pressures with uncertainty visible.</p></div></article>
    <article class="ar-sdg-card" style="--sdg-color:#56c02b"><img src="app/static/images/sdg/sdg-15.png" alt="SDG 15 official icon"><div><h4><span>Goal 15 · Nature</span>Life on Land</h4><p>Wetlands, green spaces and connected ecosystems provide environmental context for urban resilience.</p></div></article>
  </div>
  <div class="ar-sdg-footer"><span aria-hidden="true">ⓘ</span><div><strong>Evidence before impact claims.</strong> This section describes platform capabilities and contribution pathways. It does not report lives saved, emissions avoided, hectares restored or official SDG indicator progress. Those claims require independently sourced measurements and documented methods.</div></div>
  <div class="ar-sdg-note">Official SDG icons are used for informational purposes. <a href="https://sdgs.un.org/goals" target="_blank" rel="noopener">Explore the United Nations Sustainable Development Goals</a>. This publication has not been approved by the United Nations and does not reflect the views of the United Nations or its officials or Member States.</div>
</section>
    """,
    unsafe_allow_html=True,
)

st.markdown("#### Explore the related workspaces")
sdg_workspace_cols = st.columns(3, gap="medium")
with sdg_workspace_cols[0]:
    _workspace_link("app_pages/hospital_vulnerability.py", "SDG 3 · Hospital Vulnerability")
with sdg_workspace_cols[1]:
    _workspace_link("app_pages/kochi_map.py", "SDG 6 · Kochi Map")
with sdg_workspace_cols[2]:
    _workspace_link("app_pages/air_pollution.py", "SDG 9 · Air Pollution")
sdg_workspace_cols_2 = st.columns(3, gap="medium")
with sdg_workspace_cols_2[0]:
    _workspace_link("app_pages/decision_workflow.py", "SDG 11 · Decision Workflow")
with sdg_workspace_cols_2[1]:
    _workspace_link("app_pages/disaster_probability.py", "SDG 13 · Multi-Hazard Evidence")
with sdg_workspace_cols_2[2]:
    _workspace_link("app_pages/smart_mitigation_design.py", "SDG 15 · Nature-based Design Studio")

# SDGs are presented as practical entry points into the existing platform, not
# as impact claims. Each pathway opens a real workspace and keeps the evidence
# and limitations visible there.
st.markdown(
    """
    <style>
    .ar-sdg-actions {
      margin: 1.2rem 0 2.4rem;
      padding: clamp(1.15rem, 2.5vw, 1.8rem);
      border: 1px solid rgba(36,122,101,.18);
      border-radius: 22px;
      background: linear-gradient(135deg, #173f35 0%, #1e6659 58%, #286f79 100%);
      box-shadow: 0 18px 42px rgba(26,65,49,.14);
    }
    .ar-sdg-actions h3 { color:#fff!important; margin:0 0 .35rem!important; font-size:1.35rem!important; }
    .ar-sdg-actions > p { color:#d7eee1!important; margin:0 0 1rem!important; max-width:780px; line-height:1.6; }
    .ar-sdg-action-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; }
    .ar-sdg-action {
      display:flex; min-height:92px; flex-direction:column; justify-content:space-between;
      padding:.9rem 1rem; border:1px solid rgba(225,247,235,.22); border-radius:15px;
      background:rgba(255,255,255,.1); color:#f0fff5!important; text-decoration:none!important;
      transition:transform .2s ease, background .2s ease, border-color .2s ease;
    }
    .ar-sdg-action:hover { transform:translateY(-3px); background:rgba(255,255,255,.18); border-color:rgba(225,247,235,.5); }
    .ar-sdg-action strong { color:#fff!important; font-size:.86rem; }
    .ar-sdg-action span { color:#c5e7d5; font-size:.74rem; line-height:1.45; }
    .ar-sdg-action em { color:#b7f0d0; font-size:.7rem; font-style:normal; font-weight:750; }
    @media(max-width:760px){.ar-sdg-action-grid{grid-template-columns:1fr 1fr}}
    @media(max-width:480px){.ar-sdg-action-grid{grid-template-columns:1fr}.ar-sdg-action{min-height:0;gap:.45rem}}
    @media(prefers-reduced-motion:reduce){.ar-sdg-action{transition:none}.ar-sdg-action:hover{transform:none}}
    </style>
    <section class="ar-sdg-actions" aria-labelledby="ar-sdg-action-title">
      <h3 id="ar-sdg-action-title">Put the goals to work</h3>
      <p>Use the platform's evidence and planning workspaces to explore a concrete question behind each SDG. The links below are capability pathways, not claims of official SDG progress.</p>
      <div class="ar-sdg-action-grid">
        <a class="ar-sdg-action" href="/hospital_vulnerability"><strong>SDG 3 · Protect care</strong><span>Review hospital vulnerability and continuity questions.</span><em>Open hospital workspace →</em></a>
        <a class="ar-sdg-action" href="/kochi_map"><strong>SDG 6 · Understand water</strong><span>Inspect Kochi's mapped context and source coverage.</span><em>Open Kochi map →</em></a>
        <a class="ar-sdg-action" href="/air_pollution"><strong>SDG 9 · Monitor air</strong><span>Examine pollutant evidence and monitoring readiness.</span><em>Open air workspace →</em></a>
        <a class="ar-sdg-action" href="/decision_workflow"><strong>SDG 11 · Assess cities</strong><span>Move from a scenario to an evidence-gated decision review.</span><em>Open decision workflow →</em></a>
        <a class="ar-sdg-action" href="/disaster_probability"><strong>SDG 13 · Review climate risk</strong><span>Compare hazard evidence without manufactured certainty.</span><em>Open hazard review →</em></a>
        <a class="ar-sdg-action" href="/smart_mitigation_design"><strong>SDG 15 · Design with nature</strong><span>Explore transparent, nature-based mitigation concepts.</span><em>Open design studio →</em></a>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

# Footer and credits
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="ar-footer">
      <div>
        <strong>AI RESILIENCE</strong>
        Kochi environmental &amp; disaster intelligence · Evidence-first, human-centred.
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


# Kochi homepage — UX refinement layer
st.markdown(
    """
    <style>
    .ar-scope-dot {
      display:inline-block; width:8px; height:8px; margin-right:.5rem;
      border-radius:50%; background:#8ce0b6; box-shadow:0 0 0 4px rgba(140,224,182,.16);
      vertical-align:middle;
    }
    .ar-signal { grid-template-columns:repeat(4,minmax(0,1fr)); gap:.8rem; border:0; margin:1.5rem 0 0; }
    .ar-signal > div {
      min-width:0; padding:1.15rem 1.2rem; border:1px solid rgba(44,105,82,.16);
      border-radius:18px; background:rgba(255,255,255,.82); box-shadow:0 8px 24px rgba(26,65,49,.06);
    }
    .ar-signal > div:first-child { padding-left:1.2rem; }
    .ar-signal strong { color:#1d5e4b; }
    .ar-signal span { color:#247a65; letter-spacing:.11em; }
    .ar-signal p { color:#63766e; }
    .ar-story h2 { color:#1d3030 !important; }
    .ar-story p { color:#5d7068; }
    .ar-overline { color:#247a65 !important; }
    .ar-fineprint { color:#71827b; }
    .ar-gallery { gap:1rem; }
    .ar-tile { border-color:rgba(44,105,82,.16); box-shadow:0 12px 28px rgba(26,65,49,.08); }
    .ar-threat { border-color:rgba(44,105,82,.16); background:rgba(255,255,255,.76); box-shadow:0 18px 42px rgba(26,65,49,.08); }
    .ar-threat .ar-threat-bg { filter:saturate(.72) contrast(.96) brightness(1.12); }
    .ar-threat-scrim { background:linear-gradient(115deg,rgba(246,251,247,.97),rgba(239,247,241,.91) 58%,rgba(232,244,237,.82)); }
    .ar-threat .ar-story h2 { color:#1d3030 !important; }
    .ar-threat .ar-story p { color:#5d7068 !important; }
    .ar-hazard {
      border:1px solid rgba(44,105,82,.15); background:rgba(255,255,255,.82);
      box-shadow:0 8px 22px rgba(26,65,49,.045); backdrop-filter:blur(12px);
    }
    .ar-hazard:hover { border-color:rgba(36,122,101,.34); background:#fff; }
    .ar-hazard h3 { color:#23473b !important; }
    .ar-hazard p { color:#667970; }
    .ar-hazard-icon { color:#247a65; }
    .ar-why {
      border-color:rgba(44,105,82,.16);
      background:linear-gradient(145deg,rgba(255,255,255,.94),rgba(237,246,240,.92));
      box-shadow:0 18px 42px rgba(26,65,49,.075);
    }
    .ar-why .ar-story h2 { color:#1d3030 !important; }
    .ar-why .ar-story p { color:#5d7068; }
    .ar-flow-step { border-top-color:rgba(36,122,101,.42); background:linear-gradient(180deg,rgba(36,122,101,.065),rgba(36,122,101,0)); }
    .ar-step-no { color:#247a65; }
    .ar-flow-step h3 { color:#24473b !important; }
    .ar-flow-step p { color:#64766e; }
    .ar-transparency { border-color:rgba(36,122,101,.18); background:rgba(231,243,235,.78); }
    .ar-transparency strong { color:#23473b; }
    .ar-transparency p { color:#5d7068; }
    [class*="st-key-ar-nav-"] {
      border-color:rgba(44,105,82,.16);
      background:linear-gradient(145deg,rgba(255,255,255,.92),rgba(239,247,241,.9));
      box-shadow:0 12px 28px rgba(26,65,49,.06);
      transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease;
    }
    [class*="st-key-ar-nav-"]:hover { border-color:rgba(36,122,101,.34); box-shadow:0 16px 34px rgba(26,65,49,.09); }
    .ar-nav-icon { border-color:rgba(36,122,101,.18); background:rgba(36,122,101,.08); color:#247a65; }
    .ar-nav-count { color:#71827b; }
    .ar-nav-head h3 { color:#23473b !important; }
    .ar-nav-copy { color:#63766e; }
    [class*="st-key-ar-nav-"] [data-testid="stPageLink"] a { color:#315c4c !important; border-radius:10px; }
    [class*="st-key-ar-nav-"] [data-testid="stPageLink"] a:hover { color:#176b54 !important; background:rgba(36,122,101,.08); }
    .ar-sdg-section {
      border-color:rgba(44,105,82,.16);
      background:linear-gradient(145deg,rgba(255,255,255,.94),rgba(237,246,240,.94));
      box-shadow:0 18px 42px rgba(26,65,49,.07);
    }
    .ar-sdg-intro .ar-overline { color:#247a65 !important; }
    .ar-sdg-intro h2 { color:#1d3030 !important; }
    .ar-sdg-intro p { color:#5d7068 !important; }
    .ar-sdg-card { border-color:rgba(44,105,82,.14); background:rgba(255,255,255,.88); }
    .ar-sdg-card:hover { border-color:rgba(36,122,101,.32); background:#fff; }
    .ar-sdg-card h3 { color:#23473b !important; }
    .ar-sdg-card h3 span { color:#247a65 !important; }
    .ar-sdg-card p { color:#63766e !important; }
    .ar-sdg-note { color:#71827b !important; border-top-color:rgba(44,105,82,.14) !important; }
    .ar-sdg-note a { color:#176b54 !important; }
    .ar-footer { color:#71827b; }
    .ar-footer strong { color:#23473b; }
    .ar-footer .ar-foot-right { color:#71827b; }
    .ar-cine-hero :focus-visible, .ar-sdg-section a:focus-visible,
    [class*="st-key-ar-nav-"] a:focus-visible {
      outline:3px solid #e1a83a !important; outline-offset:3px !important;
    }
    @media (max-width:900px) {
      .ar-signal { grid-template-columns:repeat(2,minmax(0,1fr)); }
      .ar-flow { grid-template-columns:repeat(2,minmax(0,1fr)); }
    }
    @media (max-width:600px) {
      .ar-signal { grid-template-columns:1fr; }
      .ar-signal > div { padding:1rem; }
      .ar-flow, .ar-hazards { grid-template-columns:1fr; }
      .ar-footer .ar-foot-right { text-align:left; }
    }
    @media (prefers-reduced-motion:reduce) {
      .ar-signal > div, [class*="st-key-ar-nav-"] { transition:none !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Original cinematic homepage: compact desktop first-screen layout.
# Keeps the existing Kerala image sequence, optional local video and copy.
st.markdown(
    """
    <style>
    @media (min-width: 1200px) and (min-height: 820px) {
      .ar-cine-hero {
        box-sizing: border-box !important;
        height: 520px !important;
        min-height: 520px !important;
        padding: 2.25rem 3rem 4.15rem !important;
      }
      .ar-cine-inner {
        max-width: 820px !important;
        padding-top: .4rem !important;
      }
      .ar-cine-topline {
        margin-bottom: 1.35rem !important;
      }
      .ar-cine-title {
        font-size: clamp(3.8rem, 5.5vw, 5.2rem) !important;
        line-height: .96 !important;
      }
      .ar-cine-sub {
        max-width: 700px !important;
        margin-top: .85rem !important;
        font-size: 1.18rem !important;
        line-height: 1.35 !important;
      }
      .ar-cine-desc {
        max-width: 680px !important;
        margin-top: .55rem !important;
        font-size: .91rem !important;
        line-height: 1.5 !important;
      }
      .ar-cine-chips {
        margin-top: .8rem !important;
        gap: .4rem !important;
      }
      .ar-cine-chips span {
        padding: .3rem .62rem !important;
        font-size: .68rem !important;
      }
      .ar-cine-foot {
        bottom: 1.05rem !important;
      }
      .st-key-ar-hero-ctas {
        margin-top: -3.25rem !important;
      }
      .st-key-ar-hero-ctas [data-testid="stButton"] > button {
        min-height: 2.75rem !important;
      }
      .ar-signal {
        margin-top: 1.55rem !important;
      }
      .ar-signal > div {
        padding-top: .8rem !important;
        padding-bottom: .8rem !important;
      }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Desktop first-screen fit: tuned for a 1400 × 900 browser viewport.
# The hero and primary actions fit in the opening viewport; the informational
# sections below remain available through normal page scrolling.
st.markdown(
    """
    <style>
    @media (min-width: 1200px) and (min-height: 820px) {
      .ar-home-minimal {
        box-sizing: border-box !important;
        height: clamp(480px, calc(100svh - 330px), 570px) !important;
        min-height: clamp(480px, calc(100svh - 330px), 570px) !important;
        padding: 2.6rem 3.2rem 4.4rem !important;
      }
      .ar-home-minimal .ar-cine-inner {
        max-width: 720px !important;
      }
      .ar-home-minimal .ar-cine-title {
        font-size: clamp(3.8rem, 5.8vw, 5.2rem) !important;
        line-height: .96 !important;
      }
      .ar-home-minimal .ar-cine-sub {
        margin-top: .85rem !important;
        line-height: 1.32 !important;
      }
      .ar-home-minimal .ar-cine-desc {
        margin-top: .55rem !important;
        font-size: .93rem !important;
        line-height: 1.55 !important;
      }
      .ar-home-minimal .ar-cine-foot {
        bottom: 1.35rem !important;
      }
      .st-key-ar-hero-ctas {
        margin-top: -2.8rem !important;
      }
      .st-key-ar-hero-ctas [data-testid="stButton"] > button {
        min-height: 2.8rem !important;
      }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Home-page typography, contrast and SDG pathway refinements.
st.markdown(
    """
    <style>
    .ar-story { max-width:940px; margin:2.2rem 0 1.25rem; }
    .ar-story h2 { color:#f3f8f3 !important; font-size:clamp(1.8rem,3vw,2.55rem) !important; line-height:1.14 !important; letter-spacing:-.035em !important; font-weight:780 !important; }
    .ar-story p { color:#d2e1da !important; font-size:1.02rem !important; line-height:1.78 !important; max-width:850px; }
    .ar-overline { color:#a9c7b7 !important; font-size:.76rem !important; font-weight:800 !important; letter-spacing:.13em !important; }
    .ar-hazard h3,.ar-flow-step h3 { color:#f1f7f2 !important; font-size:1.08rem !important; line-height:1.3 !important; }
    .ar-hazard p,.ar-flow-step p,.ar-transparency p { color:#d0dfd7 !important; font-size:.91rem !important; line-height:1.7 !important; }
    .ar-fineprint { color:#c1d2c9 !important; font-size:.8rem !important; line-height:1.6 !important; }
    .ar-workspace-link { display:flex; align-items:center; justify-content:space-between; gap:.8rem; width:100%; box-sizing:border-box; margin:.42rem 0; padding:.82rem 1rem; border:1px solid rgba(169,199,183,.32); border-radius:13px; background:rgba(242,247,242,.09); color:#f3f8f3 !important; text-decoration:none !important; transition:background .18s ease,border-color .18s ease,transform .18s ease; }
    .ar-workspace-link:hover { background:rgba(169,199,183,.18); border-color:rgba(196,222,205,.7); transform:translateY(-1px); }
    .ar-workspace-link-label { color:#f3f8f3 !important; font-size:.94rem; line-height:1.4; font-weight:730; }
    .ar-workspace-link-action { color:#b9d8c6 !important; white-space:nowrap; font-size:.76rem; font-weight:750; }
    .ar-sdg-section { color:#263a35 !important; }
    .ar-sdg-kicker { font-size:.78rem !important; }
    .ar-sdg-lede { color:#40564f !important; font-size:1.04rem !important; line-height:1.8 !important; }
    .ar-sdg-callout { color:#244d43 !important; font-size:.82rem !important; }
    .ar-sdg-subhead h3 { font-size:1.3rem !important; }
    .ar-sdg-subhead p { color:#526a61 !important; font-size:.82rem !important; }
    .ar-sdg-card { min-height:164px; padding:1.05rem; }
    .ar-sdg-card h4 { font-size:1rem !important; line-height:1.38 !important; }
    .ar-sdg-card p { color:#40564f !important; font-size:.86rem !important; line-height:1.68 !important; }
    .ar-sdg-footer { color:#40564f !important; font-size:.82rem !important; line-height:1.7 !important; }
    .ar-sdg-footer strong { color:#203d36 !important; }
    .ar-sdg-note { color:#526a61 !important; font-size:.74rem !important; line-height:1.65 !important; }
    @media(max-width:700px) { .ar-workspace-link { align-items:flex-start; flex-direction:column; gap:.25rem; } .ar-workspace-link-action { white-space:normal; } }
    @media(prefers-reduced-motion:reduce) { .ar-workspace-link { transition:none; } .ar-workspace-link:hover { transform:none; } }
    </style>
    """,
    unsafe_allow_html=True,
)


# Final homepage contrast pass: force readable foregrounds on every home section.
st.markdown(
    """
    <style>
    .ar-cine-hero, .ar-home-minimal { position:relative !important; isolation:isolate !important; }
    .ar-cine-hero::before, .ar-home-minimal::before {
      background:linear-gradient(90deg,rgba(8,25,20,.90) 0%,rgba(8,25,20,.76) 58%,rgba(8,25,20,.42) 100%) !important;
      opacity:1 !important;
    }
    .ar-cine-hero .ar-cine-title, .ar-home-minimal .ar-cine-title {
      color:#FFFFFF !important; -webkit-text-fill-color:#FFFFFF !important;
      text-shadow:0 2px 12px rgba(0,0,0,.65) !important; font-weight:850 !important;
    }
    .ar-cine-hero .ar-cine-sub, .ar-home-minimal .ar-cine-sub {
      color:#F5FAF6 !important; -webkit-text-fill-color:#F5FAF6 !important;
      text-shadow:0 1px 7px rgba(0,0,0,.75) !important; font-weight:750 !important;
    }
    .ar-cine-hero .ar-cine-desc, .ar-home-minimal .ar-cine-desc,
    .ar-cine-hero .ar-cine-topline, .ar-cine-hero .ar-cine-foot,
    .ar-home-minimal .ar-cine-topline, .ar-home-minimal .ar-cine-foot {
      color:#EDF5EF !important; -webkit-text-fill-color:#EDF5EF !important;
      text-shadow:0 1px 6px rgba(0,0,0,.8) !important; font-weight:650 !important;
    }
    .ar-cine-hero .ar-cine-chips span, .ar-home-minimal .ar-cine-chips span {
      color:#FFFFFF !important; -webkit-text-fill-color:#FFFFFF !important;
      background:rgba(12,35,27,.90) !important; border:1px solid rgba(255,255,255,.52) !important; font-weight:750 !important;
    }
    .ar-story h2, .ar-hazard h3, .ar-flow-step h3 {
      color:#FFFFFF !important; -webkit-text-fill-color:#FFFFFF !important; opacity:1 !important; font-weight:800 !important;
    }
    .ar-story p, .ar-hazard p, .ar-flow-step p, .ar-transparency p, .ar-fineprint {
      color:#F0F5F1 !important; -webkit-text-fill-color:#F0F5F1 !important; opacity:1 !important; font-weight:550 !important;
    }
    .ar-overline { color:#D5EBDD !important; -webkit-text-fill-color:#D5EBDD !important; opacity:1 !important; font-weight:800 !important; }
    .ar-sdg-section {
      background:#F5F8F3 !important; color:#203D36 !important;
      border:1px solid #D6E2D8 !important; border-radius:20px !important;
    }
    .ar-sdg-section h1, .ar-sdg-section h2, .ar-sdg-section h3,
    .ar-sdg-section h4, .ar-sdg-section strong {
      color:#183A30 !important; -webkit-text-fill-color:#183A30 !important; opacity:1 !important; font-weight:800 !important;
    }
    .ar-sdg-section p, .ar-sdg-section li, .ar-sdg-section span,
    .ar-sdg-section .ar-sdg-lede, .ar-sdg-section .ar-sdg-footer,
    .ar-sdg-section .ar-sdg-note {
      color:#304A40 !important; -webkit-text-fill-color:#304A40 !important; opacity:1 !important; font-weight:550 !important;
    }
    .ar-sdg-section .ar-sdg-card {
      background:#FFFFFF !important; border:1px solid #C8D9CD !important;
      box-shadow:0 5px 16px rgba(24,58,48,.08) !important;
    }
    .ar-sdg-section .ar-sdg-card h3, .ar-sdg-section .ar-sdg-card h4 {
      color:#173D31 !important; -webkit-text-fill-color:#173D31 !important;
    }
    .ar-sdg-section .ar-sdg-card p {
      color:#344E43 !important; -webkit-text-fill-color:#344E43 !important;
    }
    .ar-sdg-section .ar-sdg-note a {
      color:#075B43 !important; -webkit-text-fill-color:#075B43 !important;
      text-decoration:underline !important; font-weight:750 !important;
    }
    .ar-workspace-link-label { color:#FFFFFF !important; -webkit-text-fill-color:#FFFFFF !important; font-weight:800 !important; }
    .ar-workspace-link-action { color:#D7EBDD !important; -webkit-text-fill-color:#D7EBDD !important; font-weight:750 !important; }
    .ar-footer, .ar-footer .ar-foot-right { color:#E2ECE5 !important; -webkit-text-fill-color:#E2ECE5 !important; }
    .ar-footer strong { color:#FFFFFF !important; -webkit-text-fill-color:#FFFFFF !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
