"""Shared visual components for the AI RESILIENCE workspace.

The design language lives in ``app.py`` so every page inherits the same tokens.
This module provides the module catalogue plus the small, accessible HTML
helpers pages use for their headers and section intros. It deliberately
contains no data or model logic.
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
    "teal": "#247A65",
    "cyan": "#2C7F8F",
    "blue": "#2F6FA8",
    "emerald": "#2F7D5E",
    "amber": "#8A6414",
    "orange": "#A9561F",
    "violet": "#6B52A8",
    "rose": "#A84848",
}

# Photographic context for each module. Every entry uses a local Kochi image so
# a module title card always has a background related to that module's subject.
MODULES: dict[str, dict[str, object]] = {
    "home": {
        "title": "Home",
        "eyebrow": "AI_RESILIENCE · KOCHI CLIMATE INTELLIGENCE",
        "description": "A Kochi-focused, evidence-first platform for environmental monitoring, multi-hazard review, critical-service resilience and mitigation planning.",
        "group": "Start here",
        "icon": "🏠",
        "image": "app/static/images/kochi/waterfront.jpg",
        "accent": "teal",
        "meta": ("Kochi pilot", "Evidence first", "Human-led decisions"),
    },
    "module-explorer": {
        "title": "Explore AI_RESILIENCE",
        "eyebrow": "AI_RESILIENCE · MODULE EXPLORER",
        "description": "Choose an existing workspace by the question you want to answer — from environmental signals and spatial context to disaster resilience and practical mitigation planning.",
        "group": "Start here",
        "icon": "🧭",
        "image": "app/static/images/kochi/waterfront.jpg",
        "accent": "teal",
        "meta": ("Existing modules", "Evidence first", "Kochi and Kerala"),
    },
    "kochi-map": {
        "title": "Kochi GIS and infrastructure map",
        "eyebrow": "AI RESILIENCE · GEOSPATIAL EVIDENCE",
        "description": "Inspect source-documented spatial layers for Kochi. The corporation boundary is an administrative outline, not a hazard or vulnerability layer, and layer status is explicit.",
        "group": "Environmental intelligence",
        "icon": "🗺️",
        "image": "app/static/images/kochi/waterfront.jpg",
        "accent": "violet",
        "meta": ("Kochi Municipal Corporation", "Source-reviewed layers", "No inferred exposure"),
    },
    "air-quality": {
        "title": "Air Quality Intelligence",
        "eyebrow": "AI RESILIENCE · ENVIRONMENTAL MONITORING",
        "description": "Historical air-quality observations, monitoring-network coverage, pollutant trends and scientific evidence assessment for Kochi, Eloor and Edayar, Kerala.",
        "group": "Environmental intelligence",
        "icon": "🌬️",
        "image": "app/static/images/kochi/industrial-coast.jpg",
        "accent": "cyan",
        "meta": ("Kochi · Kerala · India", "Eloor–Edayar industrial belt", "Historical evidence view"),
    },
    "data-readiness": {
        "title": "Data readiness",
        "eyebrow": "AI RESILIENCE · EVIDENCE & PROVENANCE",
        "description": "Check local source integrity, provenance and analysis readiness before relying on a model output. Nothing is downloaded and no raw file is rewritten.",
        "group": "Environmental intelligence",
        "icon": "🌿",
        "image": "app/static/images/kochi/mangalavanam.jpg",
        "accent": "cyan",
        "meta": ("Local source audit", "Provenance", "No downloads"),
    },
    "hospital-vulnerability": {
        "title": "Hospital Vulnerability & Accessibility",
        "eyebrow": "AI RESILIENCE · CRITICAL SERVICES",
        "description": "Explore how flood and industrial scenarios may affect hospital access, vulnerability and operational continuity across the mapped Kochi/Ernakulam urban extent.",
        "group": "Environmental intelligence",
        "icon": "🏥",
        "image": "app/static/images/kochi/water-metro.jpg",
        "accent": "emerald",
        "meta": ("Ernakulam district", "Critical services", "Preliminary screening"),
    },
    "decision-workflow": {
        "title": "Decision Workflow",
        "eyebrow": "AI RESILIENCE · DECISION SUPPORT",
        "description": "Move from a clearly described scenario through evidence gates and decision context, keeping assumptions and uncertainty visible at every step.",
        "group": "Disaster resilience",
        "icon": "🧭",
        "image": "app/static/images/kochi/backwaters.jpg",
        "accent": "teal",
        "meta": ("Scenario review", "Evidence gates", "Decision context"),
    },
    "disaster-assistant": {
        "title": "Disaster Intelligence Assistant",
        "eyebrow": "AI RESILIENCE · GROUNDED ASSISTANT",
        "description": "Ask natural-language questions grounded in reviewed project evidence, with sources and limitations kept visible.",
        "group": "Disaster resilience",
        "icon": "🧠",
        "image": "app/static/images/kochi/coast.jpg",
        "accent": "blue",
        "meta": ("Grounded assistant", "Reviewed evidence", "Human oversight"),
    },
    "compound-scenario": {
        "title": "Kochi Cyclone + Flood Resilience Workspace",
        "eyebrow": "AI RESILIENCE · COMPOUND HAZARD WORKSPACE",
        "description": "One integrated workspace for rainfall, river flooding, cyclone exposure, compound pathways and service continuity.",
        "group": "Disaster resilience",
        "icon": "⛈️",
        "image": "app/static/images/kochi/maradu.jpg",
        "accent": "violet",
        "meta": ("Kochi · Ernakulam", "Cyclone + flood", "Research prototype"),
    },
    "disaster-probability": {
        "title": "AI Disaster Risk Assessment",
        "eyebrow": "AI RESILIENCE · ERNAKULAM RISK ASSESSMENT",
        "description": "Understand local environmental conditions and assess potential disaster risks in Ernakulam, one hazard at a time.",
        "group": "Disaster resilience",
        "icon": "📊",
        "image": "app/static/images/kochi/coast.jpg",
        "accent": "blue",
        "meta": ("Ernakulam district", "Preliminary screening", "Not a forecast"),
    },
    "hazard-model-lab": {
        "title": "Hazard Model Lab",
        "eyebrow": "AI RESILIENCE · MODEL TRANSPARENCY",
        "description": "Research and training status for the multi-hazard project. A downloaded dataset is not automatically a training dataset, and a trained baseline is not an operational warning.",
        "group": "Disaster resilience",
        "icon": "🧪",
        "image": "app/static/images/kochi/industrial-coast.jpg",
        "accent": "violet",
        "meta": ("Research baselines", "Validation status", "Explicit blockers"),
    },
    "submission-ml-demo": {
        "title": "ML Evidence & Demonstration",
        "eyebrow": "AI RESILIENCE · SUBMISSION DEMONSTRATION",
        "description": "A clear, evaluator-facing view of what has been trained, what the tests show, where the models may help research, and what still needs independent validation.",
        "group": "Disaster resilience",
        "icon": "🔬",
        "image": "app/static/images/kochi/water-metro.jpg",
        "accent": "violet",
        "meta": ("Persisted research models", "Baseline comparisons", "Transparent limits"),
    },
    "mitigation-budget": {
        "title": "Urban Flood Mitigation Budget & Project Planning",
        "eyebrow": "AI RESILIENCE · KOCHI · PLANNING WORKSPACE",
        "description": "A public infrastructure planning worksheet for assessing proposed flood-mitigation investments, monitoring implementation, and keeping budget allocation transparent across Kochi, Kerala.",
        "group": "Mitigation & planning",
        "icon": "💼",
        "image": "app/static/images/kochi/fishing-nets.jpg",
        "accent": "amber",
        "meta": ("Kochi · Kerala · India", "User-supplied estimates", "Arithmetic comparison only"),
    },
    "smart-mitigation": {
        "title": "Smart Mitigation Design Studio",
        "eyebrow": "AI RESILIENCE · ENGINEERING & PLANNING",
        "description": "Kochi, Kerala · urban flood resilience concept design and budget planning. Configure an illustrative scheme and compare component costs without treating the result as construction-ready engineering.",
        "group": "Mitigation & planning",
        "icon": "🛠️",
        "image": "app/static/images/kochi/mangalavanam.jpg",
        "accent": "emerald",
        "meta": ("Kochi · Kerala · India", "Concept stage", "Engineering review required"),
    },
    "mitigation-data-intelligence": {
        "title": "Mitigation Dataset Intelligence",
        "eyebrow": "AI RESILIENCE · DATA GOVERNANCE",
        "description": "A transparent quality-control workspace for reviewing project evidence, data completeness and model readiness before investment estimates are used.",
        "group": "Mitigation & planning",
        "icon": "📋",
        "image": "app/static/images/kochi/industrial-coast.jpg",
        "accent": "cyan",
        "meta": ("Evidence-first validation", "No automatic ML unlock", "Kochi pilot"),
    },
}

# Explorer ordering: group label -> module keys in display order.
MODULE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Environmental intelligence",
        ("kochi-map", "air-quality", "hospital-vulnerability", "data-readiness"),
    ),
    (
        "Disaster resilience",
        (
            "decision-workflow",
            "disaster-assistant",
            "compound-scenario",
            "disaster-probability",
            "hazard-model-lab",
            "submission-ml-demo",
        ),
    ),
    (
        "Mitigation & planning",
        ("mitigation-budget", "smart-mitigation", "mitigation-data-intelligence"),
    ),
)

# Registered Streamlit script for each catalogue module. Keeping this beside the
# catalogue means navigation, the explorer and the shared headers cannot drift.
ROUTES: dict[str, str] = {
    "home": "app_pages/home.py",
    "module-explorer": "app_pages/module_explorer.py",
    "kochi-map": "app_pages/kochi_map.py",
    "air-quality": "app_pages/air_pollution.py",
    "data-readiness": "app_pages/data_readiness.py",
    "hospital-vulnerability": "app_pages/hospital_vulnerability.py",
    "decision-workflow": "app_pages/decision_workflow.py",
    "disaster-assistant": "app_pages/disaster_assistant.py",
    "compound-scenario": "app_pages/compound_scenario.py",
    "disaster-probability": "app_pages/disaster_probability.py",
    "hazard-model-lab": "app_pages/hazard_model_lab.py",
    "submission-ml-demo": "app_pages/submission_ml_demo.py",
    "mitigation-budget": "app_pages/mitigation_planner.py",
    "smart-mitigation": "app_pages/smart_mitigation_design.py",
    "mitigation-data-intelligence": "app_pages/mitigation_data_intelligence.py",
}

# Backwards-compatible image lookup for callers that only need a hero image.
PAGE_MEDIA: dict[str, str] = {key: str(meta["image"]) for key, meta in MODULES.items()}


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
    accent: str | None = None,
    key: str | None = None,
    as_title: bool = True,
    image: str | None = None,
) -> None:
    """Render the standard module header.

    ``st.title`` is kept for screen-reader structure and for the existing
    Streamlit tests that inspect page titles. The surrounding container is
    decorated by the shared stylesheet.

    When ``key`` matches an entry in :data:`MODULES`, the related module image,
    accent colour and icon are resolved automatically. Explicit ``image`` and
    ``accent`` arguments still take precedence.
    """

    module = MODULES.get(_slug(key or ""), {})
    resolved_key = _slug(key or title)
    accent_name = accent or str(module.get("accent") or "teal")
    accent_hex = ACCENTS.get(accent_name, ACCENTS["teal"])
    resolved_image = image or module.get("image")
    icon = str(module.get("icon") or "").strip()

    container_key = f"ar-head-{resolved_key}"
    image_css = (
        f"--ar-hero-image:url('{_escape(resolved_image)}');"
        if resolved_image
        else "--ar-hero-image:none;"
    )
    st.markdown(
        f"<style>.st-key-{container_key}{{--ar-accent:{accent_hex};{image_css}}}</style>",
        unsafe_allow_html=True,
    )
    with st.container(key=container_key):
        icon_html = f'<span class="ar-page-icon" aria-hidden="true">{_escape(icon)}</span>' if icon else ""
        st.markdown(
            f'<div class="ar-page-kicker"><span class="ar-page-dot"></span>{icon_html}{_escape(kicker)}</div>',
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


def render_page_intro(
    page_id: str,
    title: str | None = None,
    description: str | None = None,
    *,
    eyebrow: str | None = None,
    tags: Iterable[str] | None = None,
    accent: str | None = None,
    image: str | None = None,
    as_title: bool = True,
) -> None:
    """Render a module intro using the shared :data:`MODULES` catalogue.

    This is the catalogue-backed entry point used by the module explorer. Any
    value omitted by the caller is filled from the catalogue entry for
    ``page_id`` so every module title card keeps a related background image.
    """

    module = MODULES.get(_slug(page_id), {})
    resolved_title = title or str(module.get("title") or page_id.replace("-", " ").title())
    resolved_description = description if description is not None else str(module.get("description") or "")
    resolved_eyebrow = eyebrow or str(module.get("eyebrow") or "AI_RESILIENCE")
    resolved_tags = tuple(tags) if tags is not None else tuple(module.get("meta") or ())
    page_header(
        resolved_eyebrow,
        resolved_title,
        resolved_description,
        meta=resolved_tags,
        accent=accent,
        key=page_id,
        as_title=as_title,
        image=image,
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
