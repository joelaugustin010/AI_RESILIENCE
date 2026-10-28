"""PyDeck layer builders for the Kochi map."""

from pathlib import Path
from typing import Sequence

import pydeck as pdk


def build_jrc_preview_layer(image_path: Path, bounds: Sequence[float]) -> pdk.Layer:
    """Build the JRC bitmap layer from a local image path.

    PyDeck recognizes local image paths and serializes them as literal data
    URLs. Passing an already encoded ``data:image/...`` string to ``Layer``
    instead marks it as a JavaScript expression, which deck.gl cannot parse.
    """
    return pdk.Layer(
        "BitmapLayer",
        id="jrc-rp100-depth-preview",
        image=str(image_path),
        bounds=list(bounds),
        opacity=0.7,
    )
