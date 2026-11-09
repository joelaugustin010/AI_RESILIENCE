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
HEADER_IMAGES: dict[str, str] = {
    "module-explorer": "static/images/kochi/water-metro.jpg",
    "air-quality": "static/images/threats-monsoon.webp",
    "data-readiness": "static/images/kochi/mangalavanam.jpg",
    "hazard-model-lab": "static/images/kochi/backwaters.jpg",
    "hospital-vulnerability": "static/images/kochi/water-metro.jpg",
    "compound-scenario": "static/images/kochi/maradu.jpg",
    "disaster-probability": "static/images/kochi/coast.jpg",
    "mitigation-budget": "static/images/kochi/backwaters.jpg",
    "smart-mitigation": "static/images/kochi/mangalavanam.jpg",
    "mitigation-data-intelligence": "static/images/kochi/industrial-coast.jpg",
    "submission-ml-demo": "static/images/kochi/waterfront.jpg",
    "kochi-map": "static/images/kochi/waterfront.jpg",
    "disaster-assistant": "static/images/kochi/fishing-nets.jpg",
}

ACCENTS: dict[str, str] = {
    # Shared eco palette; hazard-specific colours remain distinct from severity.
    "teal": "#247A65",
    "cyan": "#83B9A5",
    "blue": "#328BCB",
    "emerald": "#31866B",
    "amber": "#C5A13A",
    "orange": "#D58A36",
    "violet": "#8064B5",
    "rose": "#C85C5C",
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
    selected_image = image or HEADER_IMAGES.get(_slug(key or title))
    image_css = (
        f"--ar-hero-image:url('{_escape(selected_image)}');"
        if selected_image
        else "--ar-hero-image:none;"
    )
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
