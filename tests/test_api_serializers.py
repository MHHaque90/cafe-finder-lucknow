"""API tests: JSON serialization adapters."""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from api.serializers import normalize_coordinate, serialize_record, to_jsonable


def test_numpy_integers_become_int():
    assert to_jsonable(np.int64(7)) == 7
    assert isinstance(to_jsonable(np.int64(7)), int)


def test_numpy_floats_become_float():
    assert to_jsonable(np.float64(1.5)) == 1.5
    assert isinstance(to_jsonable(np.float64(1.5)), float)


def test_numpy_bool_becomes_bool():
    assert to_jsonable(np.bool_(True)) is True


def test_nan_becomes_null():
    assert to_jsonable(float("nan")) is None
    assert to_jsonable(np.float64("nan")) is None


def test_pandas_missing_becomes_null():
    assert to_jsonable(pd.NA) is None
    assert to_jsonable(pd.NaT) is None


def test_lists_and_dicts_preserved():
    assert to_jsonable({"a": [np.int64(1), None]}) == {"a": [1, None]}


def test_strings_and_booleans_preserved():
    assert to_jsonable("x") == "x"
    assert to_jsonable(True) is True
    assert to_jsonable(None) is None


def test_datetime_and_path():
    assert to_jsonable(datetime(2026, 1, 1, tzinfo=timezone.utc)) == "2026-01-01T00:00:00+00:00"
    assert to_jsonable(Path("a/b")) == str(Path("a/b"))


def test_dataframe_and_series():
    df = pd.DataFrame({"a": [np.int64(1)], "b": [float("nan")]})
    assert to_jsonable(df) == [{"a": 1, "b": None}]
    assert to_jsonable(pd.Series({"x": np.int64(2)})) == {"x": 2}


def test_normalize_coordinate():
    assert normalize_coordinate("26.8") == 26.8
    assert normalize_coordinate(26.8) == 26.8
    assert normalize_coordinate("abc") is None
    assert normalize_coordinate(None) is None
    assert normalize_coordinate("") is None


def test_serialize_record_float_phone_matches_cli_display():
    record = serialize_record({"osm_id": "node1", "phone": 8874474455.0, "website": None})
    assert record["phone"] == "8874474455.0"
    assert record["website"] is None


def test_serialize_record_missing_strings_become_null():
    record = serialize_record({"osm_id": "node1", "name": "  ", "website": ""})
    assert record["name"] is None
    assert record["website"] is None
