"""Tests for dataset comparison functionality (Phase 8)."""

import pandas as pd
import pytest

from cafe_finder.compare import (
    TRACKED_FIELDS,
    compare_datasets,
    fields_equal,
    format_comparison,
    format_verbose_comparison,
)


def make_df(rows):
    """Create a DataFrame with full schema columns from dict rows."""
    return pd.DataFrame(rows)


class TestFieldsEqual:
    """Tests for fields_equal."""

    def test_both_missing(self):
        assert fields_equal(None, "")
        assert fields_equal(None, None)
        assert fields_equal("", "   ")

    def test_missing_vs_present(self):
        assert not fields_equal(None, "Cafe")
        assert not fields_equal("", "Cafe")
        assert not fields_equal("   ", "Cafe")

    def test_equal_strings(self):
        assert fields_equal("Cafe", "Cafe")

    def test_whitespace_insensitive(self):
        assert fields_equal("Cafe", "  Cafe  ")
        assert fields_equal("", "   ")

    def test_numeric_equality(self):
        assert fields_equal(26.85, 26.85)
        assert fields_equal(1, 1.0)

    def test_numeric_inequality(self):
        assert not fields_equal(26.85, 26.86)

    def test_nan_vs_value(self):
        assert not fields_equal(float("nan"), "Cafe")
        assert fields_equal(float("nan"), None)
        assert fields_equal(float("nan"), "")

    def test_zero_is_not_missing(self):
        assert not fields_equal(0, None)
        assert fields_equal(0, 0)

    def test_case_sensitive(self):
        assert fields_equal("cafe", "cafe")
        assert not fields_equal("Cafe", "cafe")


class TestCompareDatasets:
    """Tests for compare_datasets."""

    def test_identical_datasets(self):
        old = make_df([{"osm_id": "n1", "name": "A"}, {"osm_id": "n2", "name": "B"}])
        new = make_df([{"osm_id": "n1", "name": "A"}, {"osm_id": "n2", "name": "B"}])
        result = compare_datasets(old, new)
        assert result["old_record_count"] == 2
        assert result["new_record_count"] == 2
        assert len(result["added"]) == 0
        assert len(result["removed"]) == 0
        assert len(result["modified"]) == 0
        assert len(result["unchanged"]) == 2

    def test_added_records(self):
        old = make_df([{"osm_id": "n1", "name": "A"}])
        new = make_df([{"osm_id": "n1", "name": "A"}, {"osm_id": "n2", "name": "B"}])
        result = compare_datasets(old, new)
        assert len(result["added"]) == 1
        assert result["added"][0]["osm_id"] == "n2"
        assert len(result["removed"]) == 0
        assert len(result["unchanged"]) == 1

    def test_removed_records(self):
        old = make_df([{"osm_id": "n1", "name": "A"}, {"osm_id": "n2", "name": "B"}])
        new = make_df([{"osm_id": "n1", "name": "A"}])
        result = compare_datasets(old, new)
        assert len(result["removed"]) == 1
        assert result["removed"][0]["osm_id"] == "n2"
        assert len(result["added"]) == 0
        assert len(result["unchanged"]) == 1

    def test_modified_field(self):
        old = make_df([{"osm_id": "n1", "name": "A", "website": "http://old.com"}])
        new = make_df([{"osm_id": "n1", "name": "A", "website": "http://new.com"}])
        result = compare_datasets(old, new)
        assert len(result["modified"]) == 1
        item = result["modified"][0]
        assert item["osm_id"] == "n1"
        assert len(item["changes"]) == 1
        assert item["changes"][0]["field"] == "website"
        assert item["changes"][0]["old"] == "http://old.com"
        assert item["changes"][0]["new"] == "http://new.com"

    def test_added_then_removed_same_count(self):
        old = make_df([{"osm_id": "n1"}, {"osm_id": "n2"}])
        new = make_df([{"osm_id": "n1"}, {"osm_id": "n3"}])
        result = compare_datasets(old, new)
        assert len(result["added"]) == 1
        assert result["added"][0]["osm_id"] == "n3"
        assert len(result["removed"]) == 1
        assert result["removed"][0]["osm_id"] == "n2"
        assert len(result["unchanged"]) == 1
        assert result["unchanged"][0]["osm_id"] == "n1"

    def test_missing_value_equivalence(self):
        old = make_df([{"osm_id": "n1", "name": "A", "street": None, "city": ""}])
        new = make_df([{"osm_id": "n1", "name": "A", "street": "", "city": "   "}])
        result = compare_datasets(old, new)
        assert len(result["modified"]) == 0
        assert len(result["unchanged"]) == 1

    def test_field_change_from_present_to_missing(self):
        old = make_df([{"osm_id": "n1", "name": "A", "phone": "123"}])
        new = make_df([{"osm_id": "n1", "name": "A", "phone": None}])
        result = compare_datasets(old, new)
        assert len(result["modified"]) == 1
        assert result["modified"][0]["changes"][0]["field"] == "phone"

    def test_empty_old_dataset(self):
        old = make_df(pd.DataFrame(columns=["osm_id", "name"]))
        new = make_df([{"osm_id": "n1", "name": "A"}])
        result = compare_datasets(old, new)
        assert len(result["added"]) == 1
        assert len(result["removed"]) == 0
        assert len(result["unchanged"]) == 0

    def test_empty_new_dataset(self):
        old = make_df([{"osm_id": "n1", "name": "A"}])
        new = make_df(pd.DataFrame(columns=["osm_id", "name"]))
        result = compare_datasets(old, new)
        assert len(result["removed"]) == 1
        assert len(result["added"]) == 0

    def test_field_changes_count(self):
        old = make_df([{"osm_id": "n1", "name": "A", "street": "Old St", "city": "Lucknow"}])
        new = make_df([{"osm_id": "n1", "name": "A", "street": "New St", "city": "Gomti Nagar"}])
        result = compare_datasets(old, new)
        assert len(result["field_changes"]) == 2
        fields = [c["field"] for c in result["field_changes"]]
        assert "street" in fields
        assert "city" in fields

    def test_deterministic_output(self):
        old = make_df([{"osm_id": "n3"}, {"osm_id": "n1"}, {"osm_id": "n2"}])
        new = make_df([{"osm_id": "n2"}, {"osm_id": "n1"}, {"osm_id": "n4"}])
        r1 = compare_datasets(old, new)
        r2 = compare_datasets(old, new)
        assert r1["old_record_count"] == r2["old_record_count"]
        assert r1["new_record_count"] == r2["new_record_count"]
        assert len(r1["added"]) == len(r2["added"])
        assert len(r1["removed"]) == len(r2["removed"])
        assert len(r1["modified"]) == len(r2["modified"])
        assert len(r1["unchanged"]) == len(r2["unchanged"])


class TestFormatComparison:
    """Tests for format_comparison."""

    def test_summary_lines(self):
        old = make_df([{"osm_id": "n1"}])
        new = make_df([{"osm_id": "n1"}, {"osm_id": "n2"}])
        result = compare_datasets(old, new)
        output = format_comparison(result)
        assert "Dataset Comparison" in output
        assert "Previous records: 1" in output
        assert "Current records:  2" in output
        assert "Added:      1" in output
        assert "Removed:    0" in output

    def test_verbose_contains_details(self):
        old = make_df([{"osm_id": "n1", "name": "A", "website": "http://old.com"}])
        new = make_df([{"osm_id": "n1", "name": "A", "website": "http://new.com"}])
        result = compare_datasets(old, new)
        output = format_verbose_comparison(result)
        assert "website" in output
        assert "http://old.com" in output
        assert "http://new.com" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])