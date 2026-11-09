"""Integrated visual module explorer for the AI_RESILIENCE application."""

from __future__ import annotations

import streamlit as st

from src.ui_theme import MODULES, MODULE_GROUPS, ROUTES, render_page_intro


st.markdown(
    """
    <style>
    .ar-explorer-lede { max-width:850px; color:#5d756c; line-height:1.7; margin:-.4rem 0 1.4rem; }
    .ar-explorer-group { margin:1.7rem 0 .7rem; color:#247a65; font-size:.72rem; font-weight:850; letter-spacing:.14em; text-transform:uppercase; }
    .ar-explorer-card {
      min-height:205px;
      display:flex;
      flex-direction:column;
      justify-content:flex-end;
      padding:1.15rem;
      border-radius:20px;
      overflow:hidden;
      color:#fff;
      background:
        linear-gradient(180deg,rgba(5,20,18,.10) 0%,rgba(5,22,20,.72) 55%,rgba(5,22,20,.94) 100%),
        var(--explorer-image) center / cover no-repeat;
      border:1px solid rgba(255,255,255,.14);
      box-shadow:0 12px 30px rgba(24,73,55,.13);
      transition:transform .2s ease,box-shadow .2s ease;
    }
    .ar-explorer-card:hover { transform:translateY(-4px); box-shadow:0 20px 42px rgba(24,73,55,.21); }
    .ar-explorer-icon { margin-bottom:auto; font-size:1.5rem; filter:drop-shadow(0 2px 6px rgba(0,0,0,.35)); }
    .ar-explorer-card h3 { color:#fff!important; font-size:1.05rem; line-height:1.2; margin:0 0 .3rem; text-shadow:0 1px 10px rgba(0,0,0,.45); }
    .ar-explorer-card p { color:#e8f7ee!important; font-size:.8rem; line-height:1.45; margin:0; text-shadow:0 1px 8px rgba(0,0,0,.45); }
    .ar-explorer-meta { margin-top:.6rem; color:#c8f2dc; font-size:.68rem; font-weight:750; letter-spacing:.05em; text-transform:uppercase; }
    .ar-explorer-actions { margin-top:.55rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

render_page_intro("module-explorer")
st.markdown(
    '<p class="ar-explorer-lede">Every card below opens a registered application module. Outputs retain their existing provenance, uncertainty notes, calculations and data-quality safeguards.</p>',
    unsafe_allow_html=True,
)

for group_title, module_keys in MODULE_GROUPS:
    st.markdown(f'<div class="ar-explorer-group">{group_title}</div>', unsafe_allow_html=True)
    for start in range(0, len(module_keys), 3):
        columns = st.columns(3, gap="medium")
        for column, module_key in zip(columns, module_keys[start:start + 3]):
            module = MODULES.get(module_key)
            route = ROUTES.get(module_key)
            if not module or not route:
                continue
            title = str(module["title"])
            icon = str(module.get("icon") or "")
            description = str(module["description"])
            image = str(module["image"])
            meta = str((module.get("meta") or ("",))[0])
            with column:
                st.markdown(
                    f'<article class="ar-explorer-card" style="--explorer-image:url(\'{image}\')">'
                    f'<div class="ar-explorer-icon" aria-hidden="true">{icon}</div>'
                    f"<h3>{title}</h3><p>{description}</p>"
                    f'<div class="ar-explorer-meta">{meta} · Open workspace →</div></article>',
                    unsafe_allow_html=True,
                )
                st.page_link(
                    route,
                    label=f"Open {title}",
                    icon=":material/arrow_forward:",
                    use_container_width=True,
                )
