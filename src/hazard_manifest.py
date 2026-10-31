"""Display preparation for the hazard-source acquisition manifest."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from src.dataframe_display import normalize_mixed_columns_for_display


MANIFEST_COLUMNS = ["File", "Status", "Rows", "Bytes", "Retrieved", "SHA-256"]


def build_hazard_manifest_frame(
    entries: Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    """Build the Arrow-compatible display frame without changing manifest data."""
    rows = [
        {
            "File": str(item.get("file") or ""),
            "Status": str(item.get("status") or "Not recorded"),
            "Rows": "" if item.get("data_rows") is None else item["data_rows"],
            "Bytes": "" if item.get("bytes") is None else item["bytes"],
            "Retrieved": str(item.get("retrieved_at") or ""),
            "SHA-256": str(item.get("sha256") or ""),
        }
        for item in entries
    ]
    frame = pd.DataFrame(rows, columns=MANIFEST_COLUMNS)
    return normalize_mixed_columns_for_display(frame)
