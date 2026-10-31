"""Display-only normalization for mixed-type tabular data."""

from numbers import Number

import pandas as pd


def normalize_mixed_columns_for_display(frame: pd.DataFrame) -> pd.DataFrame:
    """Return an Arrow-compatible copy without changing the source frame.

    Blank strings in columns that otherwise contain numeric values are treated
    as missing. Other heterogeneous object columns are rendered as nullable
    strings so their original values remain visible without coercion errors.
    """
    display = frame.copy()
    for column in display.columns:
        values = display[column]
        if values.dtype != object:
            continue
        blank_strings = values.map(
            lambda value: isinstance(value, str) and not value.strip()
        )
        populated = values.loc[values.notna() & ~blank_strings]
        if populated.empty:
            continue

        if all(
            isinstance(value, Number) and not isinstance(value, bool)
            for value in populated
        ):
            numeric = pd.to_numeric(
                values.mask(blank_strings, pd.NA),
                errors="raise",
            )
            finite_values = numeric.dropna()
            if all(float(value).is_integer() for value in finite_values):
                if finite_values.empty or (
                    int(finite_values.min()) >= -(2**63)
                    and int(finite_values.max()) < 2**63
                ):
                    display[column] = numeric.astype("Int64")
                else:
                    display[column] = values.mask(blank_strings, pd.NA).astype("string")
            else:
                display[column] = numeric.astype("Float64")
            continue

        kinds = {
            "string"
            if isinstance(value, str)
            else "number"
            if isinstance(value, Number) and not isinstance(value, bool)
            else type(value)
            for value in populated
        }
        if len(kinds) > 1:
            display[column] = values.mask(blank_strings, pd.NA).astype("string")

    return display
