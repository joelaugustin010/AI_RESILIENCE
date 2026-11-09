"""Accessible HTML legend rendering for map layers."""
from __future__ import annotations

import re
from html import escape
from typing import Iterable


_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def render_map_legend(rows: Iterable[tuple[str, str, str]]) -> str:
    """Render layer labels, visible color swatches, and plain-language meanings."""
    items = []
    for title, color, meaning in rows:
        safe_color = color if _HEX_COLOR.fullmatch(str(color)) else "#64748B"
        items.append(
            '<div style="display:flex;align-items:flex-start;gap:12px;padding:9px 12px;'
            'border-bottom:1px solid rgba(120,130,140,.22);">'
            f'<span aria-hidden="true" style="display:inline-block;flex:0 0 18px;width:18px;'
            f'height:18px;border-radius:4px;background:{safe_color};border:1px solid rgba(0,0,0,.18);'
            'margin-top:2px;"></span>'
            '<div style="min-width:0;">'
            f'<div style="font-weight:650;">{escape(str(title))}</div>'
            f'<div style="font-size:.88em;opacity:.82;">{escape(str(meaning))}</div>'
            '</div></div>'
        )
    if not items:
        return '<div role="note">No map layers are currently displayed.</div>'
    return (
        '<div role="list" aria-label="Map legend" style="border:1px solid rgba(120,130,140,.25);'
        'border-radius:10px;overflow:hidden;">'
        + "".join(items)
        + "</div>"
    )
