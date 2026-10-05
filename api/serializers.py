"""JSON serialization adapters for Cafe Finder domain outputs.

pandas operations may produce numpy scalars, NaN, pandas NA/NaT, and
lists/dicts. These helpers convert domain outputs into valid JSON values
with explicit, type-preserving rules:

- integers stay integers (numpy integers become plain ``int``)
- floats stay floats, except NaN which becomes ``None``
- pandas NA / NaT become ``None``
- lists stay lists, dictionaries stay dictionaries
- strings stay strings, booleans stay booleans
- datetimes become ISO-8601 strings, paths become strings
- values in documented text columns use the domain's missing-value
  semantics and the CLI's display conversion (CSV type-inference
  artifacts such as float phone numbers render exactly as the CLI prints)

No value is stringified wholesale: types are preserved.
"""

import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from cafe_finder.quality import is_missing

#: Columns the dataset contract defines as text. Values pandas inferred
#: as numbers (e.g. phone/postcode floats) are rendered with the same
#: ``str(value)`` display conversion the CLI applies, so API output
#: matches CLI output exactly. Missing stays missing (``None``).
TEXT_COLUMNS = (
    "osm_id",
    "name",
    "street",
    "housenumber",
    "city",
    "postcode",
    "cuisine",
    "opening_hours",
    "website",
    "phone",
    "source",
)


def to_jsonable(value: Any) -> Any:
    """Convert a domain value into a JSON-compatible value."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, pd.DataFrame):
        return [to_jsonable(record) for record in value.to_dict(orient="records")]
    if isinstance(value, pd.Series):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, float):
        return None if math.isnan(value) else value
    if value is pd.NA or value is pd.NaT:
        return None
    # numpy scalar types (np.integer, np.floating, np.bool_, np.str_)
    # without importing numpy names directly. ``item()`` converts to the
    # nearest native Python scalar, which is then handled above.
    if type(value).__module__ == "numpy":
        try:
            return to_jsonable(value.item())
        except (ValueError, AttributeError):
            return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def normalize_coordinate(value: Any) -> float | None:
    """Coerce a dataset coordinate to ``float`` or ``None``.

    Mirrors the dataset's accepted input: numeric values and numeric
    strings become floats; missing or non-numeric values become ``None``.
    """
    try:
        number = pd.to_numeric(value, errors="coerce")
    except (TypeError, ValueError):
        return None
    if pd.isna(number):
        return None
    result = float(number)
    if math.isnan(result):
        return None
    return result


def serialize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Serialize one cafe record dict for JSON output.

    Latitude/longitude are normalized to ``float | None`` so numeric
    strings accepted by the dataset contract do not break validation.
    Text columns use the domain's missing-value semantics (missing
    becomes ``None``) and the CLI's display conversion for values
    pandas inferred as numbers. Every other value passes through
    :func:`to_jsonable` unchanged.
    """
    normalized = dict(record)
    for column in ("latitude", "longitude"):
        if column in normalized:
            normalized[column] = normalize_coordinate(normalized[column])
    for column in TEXT_COLUMNS:
        if column in normalized:
            value = normalized[column]
            if is_missing(value):
                normalized[column] = None
            elif not isinstance(value, str):
                normalized[column] = str(value).strip()
    return to_jsonable(normalized)


def serialize_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Serialize a cafes DataFrame into a list of JSON-ready records."""
    return [serialize_record(record) for record in df.to_dict(orient="records")]
