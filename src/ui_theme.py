"""Shared visual components for the AI RESILIENCE workspace.

The design language lives in ``app.py`` so every page inherits the same tokens.
This module provides the small, accessible HTML helpers pages use for their
headers and section intros. It deliberately contains no data or model logic.
"""

from __future__ import annotations

import html
import re
from typing import Iterable

import streamlit as st


# One accent per module family. The values are also exposed as CSS variables so
# page headers keep their own character while sharing typography and spacing.
ACCENTS: dict[str, str] = {
    # Shared eco palette; hazard-specific colours remain distinct from severity.
    "teal": "#174E55",
    "cyan": "#299B91",
    "blue": "#4F8290",
    "emerald": "#4F8A76",
    "amber": "#9A6A25",
    "orange": "#B97845",
    "violet": "#76669A",
    "rose": "#B94343",
}

# Local, reviewed visual context for each workspace. These are presentation
# assets only; analytical outputs continue to come from the existing data
# pipelines and retain their provenance and uncertainty boundaries.
PAGE_MEDIA: dict[str, str] = {
    "air-quality": "app/static/images/threats-monsoon.webp",
    "compound-scenario": "app/static/images/hero-kerala-coast.jpg",
    "data-readiness": "app/static/images/beauty-forest.webp",
    "disaster-assistant": "app/static/images/beauty-backwaters.webp",
    "disaster-probability": "app/static/images/hero-kerala-fallback.jpg",
    "hazard-model-lab": "app/static/images/beauty-ghats.webp",
    "hospital-vulnerability": "app/static/images/beauty-city.webp",
    "kochi-map": "app/static/images/beauty-city.webp",
    "mitigation-budget": "app/static/images/hero-kerala-flood-road.jpg",
    "mitigation-data-intelligence": "app/static/images/beauty-forest.webp",
    "smart-mitigation": "app/static/images/beauty-waterfall.webp",
    "submission-ml-demo": "app/static/images/beauty-forest.webp",
    "decision-workflow": "app/static/images/beauty-coast.webp",
    "module-explorer": "app/static/images/beauty-backwaters.webp",
}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "page"


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _meta_html(meta: Iterable[str]) -> str:
    chips = "".join(f"<span>{_escape(item)}</span>" for item in meta if str(item).strip())
    return f'<div class="ar-page-meta">{chips}</div>' if chips else ""


def _render_workspace_design_system() -> None:
    """Apply the shared environmental surface treatment to every workspace.

    ``app.py`` owns the application shell, but Streamlit renders page-level
    widgets after that shell's stylesheet.  Keeping this small, high-specificity
    contract here means every page that calls :func:`page_header` gets the same
    readable surfaces, controls, photo masthead, and responsive behaviour.  It
    changes presentation only; it does not style chart/map internals or alter
    analytical state.
    """

    st.markdown(
        """
        <style>
        /* Workspace surface: ivory, forest, water, and earth. */
        [data-testid="stMain"] {
          --ar-surface: #fbfaf4;
          --ar-surface-raised: #ffffff;
          --ar-ink: #193b35;
          --ar-muted: #4e6861;
          --ar-border: rgba(23, 78, 85, .16);
          color: var(--ar-ink) !important;
          font-family: Inter, "Segoe UI", Arial, sans-serif !important;
        }
        [data-testid="stMain"] > div {
          background: linear-gradient(180deg, rgba(251,250,244,.98), rgba(247,250,246,.98)) !important;
        }
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] li,
        [data-testid="stMain"] [data-testid="stCaptionContainer"] {
          color: var(--ar-muted) !important;
          font-family: Inter, "Segoe UI", Arial, sans-serif !important;
          font-size: .96rem !important;
          line-height: 1.68 !important;
        }
        [data-testid="stMain"] h1,
        [data-testid="stMain"] h2,
        [data-testid="stMain"] h3,
        [data-testid="stMain"] h4 {
          color: var(--ar-ink) !important;
          font-family: Inter, "Segoe UI", Arial, sans-serif !important;
          letter-spacing: -.025em !important;
          font-weight: 780 !important;
        }
        [data-testid="stMain"] h2 { font-size: clamp(1.35rem, 2.2vw, 2rem) !important; }
        [data-testid="stMain"] h3 { font-size: clamp(1.08rem, 1.6vw, 1.4rem) !important; }

        /* Module photography: keep the real local image visible behind the copy. */
        [data-testid="stMain"] [class*="st-key-ar-head-"] {
          position: relative !important;
          overflow: hidden !important;
          isolation: isolate !important;
          min-height: 245px !important;
          margin: .2rem 0 1.45rem !important;
          padding: clamp(1.45rem, 3.2vw, 2.55rem) !important;
          border: 1px solid rgba(224, 246, 241, .26) !important;
          border-radius: 26px !important;
          background-image:
            linear-gradient(105deg, rgba(3, 27, 24, .94) 0%, rgba(7, 53, 48, .73) 54%, rgba(7, 39, 47, .38) 100%),
            var(--ar-hero-image),
            linear-gradient(125deg, #173f35, #1b6670) !important;
          background-position: center !important;
          background-size: cover !important;
          box-shadow: 0 22px 52px rgba(17, 64, 50, .18) !important;
        }
        [data-testid="stMain"] [class*="st-key-ar-head-"]::after {
          content: "" !important;
          position: absolute !important;
          inset: 0 !important;
          z-index: -1 !important;
          background: linear-gradient(180deg, rgba(5, 28, 25, .05), rgba(5, 28, 25, .5)) !important;
          pointer-events: none !important;
        }
        [data-testid="stMain"] [class*="st-key-ar-head-"] > div {
          position: relative !important;
          z-index: 1 !important;
        }
        [data-testid="stMain"] [class*="st-key-ar-head-"] h1,
        [data-testid="stMain"] [class*="st-key-ar-head-"] .ar-page-title {
          color: #fff !important;
          -webkit-text-fill-color: #fff !important;
          font-size: clamp(2.05rem, 4.2vw, 3.5rem) !important;
          font-weight: 820 !important;
          line-height: 1.08 !important;
          text-shadow: 0 2px 18px rgba(0, 0, 0, .34) !important;
        }
        [data-testid="stMain"] [class*="st-key-ar-head-"] .ar-page-kicker,
        [data-testid="stMain"] [class*="st-key-ar-head-"] .ar-page-kicker *,
        [data-testid="stMain"] [class*="st-key-ar-head-"] .ar-page-meta,
        [data-testid="stMain"] [class*="st-key-ar-head-"] .ar-page-meta * {
          color: #c8f2df !important;
          -webkit-text-fill-color: #c8f2df !important;
          opacity: 1 !important;
        }
        [data-testid="stMain"] [class*="st-key-ar-head-"] .ar-page-copy,
        [data-testid="stMain"] [class*="st-key-ar-head-"] .ar-page-copy * {
          color: #f1faf5 !important;
          -webkit-text-fill-color: #f1faf5 !important;
          max-width: 850px !important;
          font-size: clamp(.98rem, 1.3vw, 1.12rem) !important;
          line-height: 1.65 !important;
        }
        [data-testid="stMain"] [class*="st-key-ar-head-"] .ar-page-meta span {
          color: #f1faf5 !important;
          background: rgba(7, 63, 52, .58) !important;
          border: 1px solid rgba(220, 247, 228, .38) !important;
          border-radius: 999px !important;
        }

        /* Every analytical surface gets the same quiet elevation. */
        [data-testid="stMain"] [data-testid="stMetric"],
        [data-testid="stMain"] [data-testid="stExpander"],
        [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stMain"] [data-testid="stAlert"] {
          border-radius: 18px !important;
        }
        [data-testid="stMain"] [data-testid="stMetric"],
        [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
          background: rgba(255, 255, 255, .86) !important;
          border: 1px solid var(--ar-border) !important;
          box-shadow: 0 10px 26px rgba(23, 78, 85, .06) !important;
        }
        [data-testid="stMain"] [data-testid="stExpander"] {
          background: rgba(255, 255, 255, .72) !important;
          border: 1px solid var(--ar-border) !important;
        }
        [data-testid="stMain"] [data-testid="stExpander"] summary,
        [data-testid="stMain"] [data-testid="stExpander"] summary p {
          color: #174e55 !important;
          font-weight: 720 !important;
        }
        [data-testid="stMain"] [data-testid="stMetricLabel"],
        [data-testid="stMain"] [data-testid="stMetricLabel"] * {
          color: #54706a !important;
        }
        [data-testid="stMain"] [data-testid="stMetricValue"],
        [data-testid="stMain"] [data-testid="stMetricValue"] * {
          color: #174e55 !important;
        }

        /* Inputs and actions remain recognisable and keyboard-friendly. */
        [data-testid="stMain"] input,
        [data-testid="stMain"] textarea,
        [data-testid="stMain"] [data-baseweb="select"] > div {
          background: #fff !important;
          border-color: rgba(23, 78, 85, .22) !important;
          color: #193b35 !important;
          border-radius: 11px !important;
        }
        [data-testid="stMain"] input::placeholder,
        [data-testid="stMain"] textarea::placeholder { color: #718783 !important; opacity: 1 !important; }
        [data-testid="stMain"] div.stButton > button,
        [data-testid="stMain"] button[kind="primary"] {
          border-radius: 12px !important;
          border: 1px solid rgba(23, 78, 85, .22) !important;
          background: #174e55 !important;
          color: #fff !important;
          font-weight: 720 !important;
          min-height: 2.55rem !important;
          transition: transform .2s ease, box-shadow .2s ease, background .2s ease !important;
        }
        [data-testid="stMain"] div.stButton > button:hover,
        [data-testid="stMain"] button[kind="primary"]:hover {
          background: #216e68 !important;
          box-shadow: 0 8px 20px rgba(23, 78, 85, .18) !important;
          transform: translateY(-1px) !important;
        }
        [data-testid="stMain"] [data-testid="stTabs"] button { color: #4e6861 !important; font-weight: 680 !important; }
        [data-testid="stMain"] [data-testid="stTabs"] button[aria-selected="true"] { color: #174e55 !important; }
        [data-testid="stMain"] a { color: #176f70 !important; }

        @media (max-width: 760px) {
          [data-testid="stMain"] [class*="st-key-ar-head-"] { min-height: 220px !important; border-radius: 19px !important; padding: 1.25rem !important; }
          [data-testid="stMain"] [class*="st-key-ar-head-"] h1 { font-size: clamp(1.8rem, 9vw, 2.55rem) !important; }
          [data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
          [data-testid="stMain"] [data-testid="stMarkdownContainer"] li { font-size: .93rem !important; }
        }
        @media (prefers-reduced-motion: reduce) {
          [data-testid="stMain"] *, [data-testid="stMain"] *::before, [data-testid="stMain"] *::after {
            animation-duration: .01ms !important; animation-iteration-count: 1 !important;
            scroll-behavior: auto !important; transition-duration: .01ms !important;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(
    kicker: str,
    title: str,
    description: str,
    *,
    meta: Iterable[str] = (),
    accent: str = "teal",
    key: str | None = None,
    as_title: bool = True,
    image: str | None = None,
) -> None:
    """Render the standard module header.

    ``st.title`` is kept for screen-reader structure and for the existing
    Streamlit tests that inspect page titles. The surrounding container is
    decorated by the shared stylesheet.
    """

    _render_workspace_design_system()
    accent_hex = ACCENTS.get(accent, ACCENTS["teal"])
    container_key = f"ar-head-{_slug(key or title)}"
    hero_image = image or PAGE_MEDIA.get(_slug(key or title))
    image_css = f"--ar-hero-image:url('{_escape(hero_image)}');" if hero_image else "--ar-hero-image:none;"
    st.markdown(
        f"<style>.st-key-{container_key}{{--ar-accent:{accent_hex};{image_css}}}</style>",
        unsafe_allow_html=True,
    )
    with st.container(key=container_key):
        st.markdown(
            f'<div class="ar-page-kicker"><span class="ar-page-dot"></span>{_escape(kicker)}</div>',
            unsafe_allow_html=True,
        )
        if as_title:
            st.title(title)
        else:
            st.markdown(f'<div class="ar-page-title">{_escape(title)}</div>', unsafe_allow_html=True)
        if description:
            st.markdown(
                f'<p class="ar-page-copy">{_escape(description)}</p>',
                unsafe_allow_html=True,
            )
        if meta:
            st.markdown(_meta_html(meta), unsafe_allow_html=True)
    research_status_notice(title)


def render_page_intro(
    page_id: str,
    title: str,
    description: str,
    *,
    eyebrow: str = "AI_RESILIENCE · ENVIRONMENTAL INTELLIGENCE",
    tags: tuple[str, ...] = (),
) -> None:
    """Compatibility wrapper for photo-backed module introductions.

    New and legacy workspaces use the same masthead implementation, so adding
    a page cannot silently reintroduce the old unstyled title treatment.
    """
    page_header(
        eyebrow,
        title,
        description,
        meta=tags,
        key=page_id,
    )


def section_intro(overline: str, title: str, description: str = "") -> None:
    """Compact section intro used between major blocks on analytical pages."""

    copy = f"<p>{_escape(description)}</p>" if description else ""
    st.markdown(
        f'<div class="ar-sec-intro"><span class="ar-sec-overline">{_escape(overline)}</span>'
        f"<h2>{_escape(title)}</h2>{copy}</div>",
        unsafe_allow_html=True,
    )


def risk_badge(label: str, level: str = "moderate") -> str:
    """Return an accessible risk pill in the shared colour language.

    ``level`` is one of ``safe``, ``moderate``, ``high`` or ``critical``.
    Intended for use inside an ``unsafe_allow_html`` markdown block.
    """

    allowed = {"safe", "moderate", "high", "critical"}
    tone = level if level in allowed else "moderate"
    return f'<span class="ar-risk ar-risk-{tone}">{_escape(label)}</span>'


def research_status_notice(scope: str = "This workspace") -> None:
    """Display the platform-wide evidence-gated research status in every workspace."""
    label = str(scope).strip() or "This workspace"
    st.warning(
        f"RESEARCH-GRADE SCREENING · {label}. AI_RESILIENCE is a research demonstration "
        "and decision-support platform, not an operational early-warning service. "
        "Outputs are conditional on supplied evidence; unvalidated probabilities, "
        "predicted inundation depths, verified affected-population counts, and proven "
        "intervention benefits are not claimed. Check source, timestamp, coverage, "
        "uncertainty and data gaps before interpreting any result. Follow official "
        "IMD, CWC, KSDMA and local-authority instructions for real safety decisions."
    )
