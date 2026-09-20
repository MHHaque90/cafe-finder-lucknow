"""Tests for schema validation (Phase 10)."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from cafe_finder.schema import (
    SCHEMA_VERSION,
    CANONICAL_COLUMNS,
    REQUIRED_COLUMNS,
    validate_schema,
)


def make_valid_df() -> pd.DataFrame:
    """Create a valid DataFrame with all 13 canonical columns."""
    return pd.DataFrame([{
        "osm_id": "node12345",
        "name": "Test Cafe",
        "latitude": 26.85,
        "longitude": 80.95,
        "street": "Test Street",
        "housenumber": "123",
        "city": "Lucknow",
        "postcode": "226001",
        "cuisine": "cafe",
        "opening_hours": "08:00-22:00",
        "website": "http://example.com",
        "phone": "+91-1234567890",
        "source": "OpenStreetMap",
    }])


class TestSchemaValidation:
    """Tests for schema.validate_schema()."""

    def test_canonical_schema_passes(self):
        df = make_valid_df()
        result = validate_schema(df)
        assert result["valid"] is True
        assert result["schema_version"] == SCHEMA_VERSION
        assert result["missing_columns"] == []
        assert result["unexpected_columns"] == []
        assert result["invalid_types"] == {}
        assert result["column_order_valid"] is True

    def test_correct_column_order_passes(self):
        df = make_valid_df()[CANONICAL_COLUMNS]
        result = validate_schema(df)
        assert result["valid"] is True
        assert result["column_order_valid"] is True

    def test_missing_column_fails(self):
        df = make_valid_df().drop(columns=["name"])
        result = validate_schema(df)
        assert result["valid"] is False
        assert "name" in result["missing_columns"]

    def test_unexpected_column_fails(self):
        df = make_valid_df()
        df["extra_column"] = "extra"
        result = validate_schema(df)
        assert result["valid"] is False
        assert "extra_column" in result["unexpected_columns"]

    def test_incorrect_column_order_fails(self):
        df = make_valid_df()[list(reversed(CANONICAL_COLUMNS))]
        result = validate_schema(df)
        assert result["valid"] is False
        assert result["column_order_valid"] is False

    def test_valid_string_fields(self):
        df = make_valid_df()
        result = validate_schema(df)
        assert result["valid"] is True

    def test_nullable_source_allowed(self):
        df = make_valid_df()
        df["source"] = None
        result = validate_schema(df)
        assert result["valid"] is True

        df["source"] = ""
        result = validate_schema(df)
        assert result["valid"] is True

        df["source"] = "   "
        result = validate_schema(df)
        assert result["valid"] is True

    def test_invalid_non_string_source_rejected(self):
        df = make_valid_df()
        df["source"] = 123
        result = validate_schema(df)
        assert result["valid"] is False
        assert "source" in result["invalid_types"]

        df["source"] = 45.6
        result = validate_schema(df)
        assert result["valid"] is False

        df["source"] = True
        result = validate_schema(df)
        assert result["valid"] is False

    def test_valid_numeric_coordinates(self):
        df = make_valid_df()
        df["latitude"] = 26.85
        df["longitude"] = 80.95
        result = validate_schema(df)
        assert result["valid"] is True

    def test_numeric_string_coordinates_accepted(self):
        df = make_valid_df()
        df["latitude"] = "26.85"
        df["longitude"] = "80.95"
        result = validate_schema(df)
        assert result["valid"] is True

    def test_invalid_coordinate_types_rejected(self):
        df = make_valid_df()
        df["latitude"] = "abc"
        result = validate_schema(df)
        assert result["valid"] is False
        assert "latitude" in result["invalid_types"]

        df = make_valid_df()
        df["latitude"] = None
        result = validate_schema(df)
        assert result["valid"] is False

    def test_valid_non_empty_string_osm_id(self):
        for valid_id in ["node12345", "way67890", "relation99999"]:
            df = make_valid_df()
            df["osm_id"] = valid_id
            result = validate_schema(df)
            assert result["valid"] is True, f"Failed for {valid_id}"

    def test_missing_osm_id_rejected(self):
        df = make_valid_df()
        df["osm_id"] = None
        result = validate_schema(df)
        assert result["valid"] is False
        assert "osm_id" in result["invalid_types"]

    def test_empty_osm_id_rejected(self):
        df = make_valid_df()
        df["osm_id"] = ""
        result = validate_schema(df)
        assert result["valid"] is False
        assert "osm_id" in result["invalid_types"]

    def test_whitespace_only_osm_id_rejected(self):
        df = make_valid_df()
        df["osm_id"] = "   "
        result = validate_schema(df)
        assert result["valid"] is False
        assert "osm_id" in result["invalid_types"]

    def test_numeric_osm_id_rejected(self):
        df = make_valid_df()
        df["osm_id"] = 12345
        result = validate_schema(df)
        assert result["valid"] is False
        assert "osm_id" in result["invalid_types"]

        df["osm_id"] = 12345.0
        result = validate_schema(df)
        assert result["valid"] is False

        df["osm_id"] = True
        result = validate_schema(df)
        assert result["valid"] is False

    def test_empty_dataframe_with_correct_columns_valid(self):
        df = pd.DataFrame(columns=CANONICAL_COLUMNS)
        result = validate_schema(df)
        assert result["valid"] is True

    def test_deterministic_validation_results(self):
        df = make_valid_df()
        result1 = validate_schema(df)
        result2 = validate_schema(df)
        assert result1 == result2
        # Check key ordering in invalid_types is deterministic
        df_bad = make_valid_df()
        df_bad["source"] = 123
        df_bad["latitude"] = "abc"
        result = validate_schema(df_bad)
        # invalid_types keys should be in canonical column order
        keys = list(result["invalid_types"].keys())
        assert keys == sorted(keys, key=lambda x: CANONICAL_COLUMNS.index(x) if x in CANONICAL_COLUMNS else 999)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])