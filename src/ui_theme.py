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
