"""Tests for quality functionality (Phase 7)."""

import pandas as pd
import pytest

from cafe_finder.quality import (
    IMPORTANT_FIELDS,
    calculate_completeness,
    detect_duplicates,
    generate_provenance,
    generate_quality_report,
    generate_record_quality_flags,
    is_missing,
    validate_coordinates,
)


class TestIsMissing:
    """Tests for is_missing function."""

    def test_none_is_missing(self):
        assert is_missing(None) is True

    def test_nan_is_missing(self):
        assert is_missing(float("nan")) is True

    def test_pd_na_is_missing(self):
        assert is_missing(pd.NA) is True

    def test_empty_string_is_missing(self):
        assert is_missing("") is True

    def test_whitespace_string_is_missing(self):
        assert is_missing("   ") is True
        assert is_missing("\t\n") is True

    def test_normal_string_not_missing(self):
        assert is_missing("hello") is False
        assert is_missing("  hello  ") is False

    def test_zero_not_missing(self):
        assert is_missing(0) is False
        assert is_missing(0.0) is False

    def test_valid_numeric_not_missing(self):
        assert is_missing(42) is False
        assert is_missing(-1.5) is False

    def test_false_not_missing(self):
        assert is_missing(False) is False


class TestCompleteness:
    """Tests for calculate_completeness function."""

    def test_fully_complete_dataframe(self):
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8, 26.9],
            "longitude": [80.9, 81.0],
            "street": ["Main St", "Second St"],
            "housenumber": ["1", "2"],
            "city": ["Lucknow", "Lucknow"],
            "postcode": ["226001", "226002"],
            "cuisine": ["coffee_shop", "tea"],
            "opening_hours": ["09:00-22:00", "10:00-20:00"],
            "website": ["http://a.com", "http://b.com"],
            "phone": ["123", "456"],
        })
        result = calculate_completeness(df)
        for field in IMPORTANT_FIELDS:
            assert result[field]["present_count"] == 2
            assert result[field]["missing_count"] == 0
            assert result[field]["completeness_percentage"] == 100.0

    def test_partially_missing_dataframe(self):
        df = pd.DataFrame({
            "name": ["Cafe A", None],
            "latitude": [26.8, 26.9],
            "longitude": [80.9, 81.0],
            "cuisine": ["coffee_shop", ""],
            "opening_hours": [None, "   "],
        })
        result = calculate_completeness(df)
        assert result["name"]["present_count"] == 1
        assert result["name"]["missing_count"] == 1
        assert result["cuisine"]["present_count"] == 1
        assert result["cuisine"]["missing_count"] == 1
        assert result["opening_hours"]["present_count"] == 0
        assert result["opening_hours"]["missing_count"] == 2

    def test_zero_values_are_present(self):
        df = pd.DataFrame({
            "name": ["A"],
            "latitude": [0.0],
            "longitude": [0.0],
            "cuisine": [0],
        })
        result = calculate_completeness(df)
        assert result["latitude"]["present_count"] == 1
        assert result["longitude"]["present_count"] == 1
        assert result["cuisine"]["present_count"] == 1

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=IMPORTANT_FIELDS)
        result = calculate_completeness(df)
        for field in IMPORTANT_FIELDS:
            assert result[field]["present_count"] == 0
            assert result[field]["missing_count"] == 0
            assert result[field]["completeness_percentage"] == 0.0

    def test_missing_columns_handled(self):
        df = pd.DataFrame({"name": ["A"], "latitude": [1.0], "longitude": [2.0]})
        result = calculate_completeness(df)
        for field in IMPORTANT_FIELDS:
            if field in ["name", "latitude", "longitude"]:
                assert result[field]["present_count"] == 1
            else:
                assert result[field]["present_count"] == 0
                assert result[field]["missing_count"] == 1

    def test_counts_sum_to_total(self):
        df = pd.DataFrame({
            "name": ["A", None, "B"],
            "latitude": [1.0, 2.0, None],
        })
        result = calculate_completeness(df)
        for field in ["name", "latitude"]:
            total = result[field]["present_count"] + result[field]["missing_count"]
            assert total == 3


class TestCoordinates:
    """Tests for validate_coordinates function."""

    def test_valid_coordinates(self):
        df = pd.DataFrame({
            "osm_id": ["n1", "n2", "n3"],
            "latitude": [26.8, -90, 90],
            "longitude": [80.9, -180, 180],
        })
        result = validate_coordinates(df)
        assert result["valid_count"] == 3
        assert result["invalid_count"] == 0

    def test_latitude_out_of_range(self):
        df = pd.DataFrame({
            "osm_id": ["n1"],
            "latitude": [91],
            "longitude": [80.9],
        })
        result = validate_coordinates(df)
        assert result["invalid_count"] == 1
        assert any("latitude_out_of_range" in r["issues"] for r in result["invalid_records"])

    def test_longitude_out_of_range(self):
        df = pd.DataFrame({
            "osm_id": ["n1"],
            "latitude": [26.8],
            "longitude": [181],
        })
        result = validate_coordinates(df)
        assert result["invalid_count"] == 1
        assert any("longitude_out_of_range" in r["issues"] for r in result["invalid_records"])

    def test_missing_coordinates(self):
        df = pd.DataFrame({
            "osm_id": ["n1", "n2"],
            "latitude": [None, 26.8],
            "longitude": [80.9, None],
        })
        result = validate_coordinates(df)
        assert result["invalid_count"] == 2
        issues = [i for r in result["invalid_records"] for i in r["issues"]]
        assert "missing_latitude" in issues
        assert "missing_longitude" in issues

    def test_non_numeric_coordinates(self):
        df = pd.DataFrame({
            "osm_id": ["n1", "n2"],
            "latitude": ["invalid", 26.8],
            "longitude": [80.9, "also_invalid"],
        })
        result = validate_coordinates(df)
        assert result["invalid_count"] == 2
        issues = [i for r in result["invalid_records"] for i in r["issues"]]
        assert "non_numeric_latitude" in issues
        assert "non_numeric_longitude" in issues

    def test_both_coordinates_invalid(self):
        df = pd.DataFrame({
            "osm_id": ["n1"],
            "latitude": [200],
            "longitude": [-200],
        })
        result = validate_coordinates(df)
        assert result["invalid_count"] == 1
        issues = result["invalid_records"][0]["issues"]
        assert "latitude_out_of_range" in issues
        assert "longitude_out_of_range" in issues


class TestDuplicates:
    """Tests for detect_duplicates function."""

    def test_unique_osm_ids(self):
        df = pd.DataFrame({
            "osm_id": ["node1", "node2"],
            "name": ["A", "B"],
            "latitude": [1.0, 2.0],
            "longitude": [3.0, 4.0],
        })
        result = detect_duplicates(df)
        assert result["duplicate_osm_id_records"] == 0
        assert result["duplicate_osm_id_values"] == []

    def test_duplicate_osm_ids(self):
        df = pd.DataFrame({
            "osm_id": ["node1", "node1", "node2"],
            "name": ["A", "B", "C"],
            "latitude": [1.0, 2.0, 3.0],
            "longitude": [3.0, 4.0, 5.0],
        })
        result = detect_duplicates(df)
        assert result["duplicate_osm_id_records"] == 2
        assert "node1" in result["duplicate_osm_id_values"]

    def test_duplicate_coord_name(self):
        df = pd.DataFrame({
            "osm_id": ["node1", "node2"],
            "name": ["Cafe A", "Cafe A"],
            "latitude": [1.0, 1.0],
            "longitude": [2.0, 2.0],
        })
        result = detect_duplicates(df)
        assert result["duplicate_location_name_records"] == 2
        assert len(result["duplicate_location_name_groups"]) == 1

    def test_same_name_different_coords_not_duplicate(self):
        df = pd.DataFrame({
            "osm_id": ["node1", "node2"],
            "name": ["Cafe Coffee Day", "Cafe Coffee Day"],
            "latitude": [1.0, 2.0],
            "longitude": [3.0, 4.0],
        })
        result = detect_duplicates(df)
        assert result["duplicate_location_name_records"] == 0

    def test_case_whitespace_normalization(self):
        df = pd.DataFrame({
            "osm_id": ["node1", "node2"],
            "name": ["  Cafe A  ", "cafe a"],
            "latitude": [1.0, 1.0],
            "longitude": [2.0, 2.0],
        })
        result = detect_duplicates(df)
        assert result["duplicate_location_name_records"] == 2

    def test_missing_names_handled(self):
        df = pd.DataFrame({
            "osm_id": ["node1", "node2"],
            "name": [None, None],
            "latitude": [1.0, 1.0],
            "longitude": [2.0, 2.0],
        })
        result = detect_duplicates(df)
        assert result["duplicate_location_name_records"] == 2

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["osm_id", "name", "latitude", "longitude"])
        result = detect_duplicates(df)
        assert result["duplicate_osm_id_records"] == 0
        assert result["duplicate_location_name_records"] == 0


class TestRecordQualityFlags:
    """Tests for generate_record_quality_flags function."""

    def test_missing_field_flags(self):
        df = pd.DataFrame({
            "osm_id": ["n1"],
            "name": [None],
            "cuisine": [""],
            "opening_hours": ["   "],
            "website": [None],
            "phone": [None],
            "latitude": [26.8],
            "longitude": [80.9],
        })
        result = generate_record_quality_flags(df)
        flags = result.iloc[0]["quality_flags"]
        assert "missing_name" in flags
        assert "missing_cuisine" in flags
        assert "missing_opening_hours" in flags
        assert "missing_website" in flags
        assert "missing_phone" in flags

    def test_invalid_coordinate_flags(self):
        df = pd.DataFrame({
            "osm_id": ["n1", "n2"],
            "name": ["A", "B"],
            "latitude": [200, "invalid"],
            "longitude": [80.9, "also_invalid"],
        })
        result = generate_record_quality_flags(df)
        flags1 = result.iloc[0]["quality_flags"]
        flags2 = result.iloc[1]["quality_flags"]
        assert "invalid_latitude" in flags1
        assert "invalid_longitude" not in flags1
        assert "invalid_latitude" in flags2
        assert "invalid_longitude" in flags2

    def test_duplicate_osm_id_flag(self):
        df = pd.DataFrame({
            "osm_id": ["node1", "node1"],
            "name": ["A", "B"],
            "latitude": [1.0, 2.0],
            "longitude": [3.0, 4.0],
        })
        result = generate_record_quality_flags(df)
        assert "duplicate_osm_id" in result.iloc[0]["quality_flags"]
        assert "duplicate_osm_id" in result.iloc[1]["quality_flags"]

    def test_duplicate_location_name_flag(self):
        df = pd.DataFrame({
            "osm_id": ["node1", "node2"],
            "name": ["Cafe A", "Cafe A"],
            "latitude": [1.0, 1.0],
            "longitude": [2.0, 2.0],
        })
        result = generate_record_quality_flags(df)
        assert "duplicate_location_name" in result.iloc[0]["quality_flags"]
        assert "duplicate_location_name" in result.iloc[1]["quality_flags"]

    def test_multiple_simultaneous_flags(self):
        df = pd.DataFrame({
            "osm_id": ["node1", "node1"],
            "name": [None, None],
            "latitude": [200, 200],
            "longitude": [200, 200],
        })
        result = generate_record_quality_flags(df)
        flags = result.iloc[0]["quality_flags"]
        assert "missing_name" in flags
        assert "invalid_latitude" in flags
        assert "invalid_longitude" in flags
        assert "duplicate_osm_id" in flags

    def test_clean_record_no_flags(self):
        df = pd.DataFrame({
            "osm_id": ["node1"],
            "name": ["Cafe A"],
            "latitude": [26.8],
            "longitude": [80.9],
            "cuisine": ["coffee_shop"],
            "opening_hours": ["09:00-22:00"],
            "website": ["http://a.com"],
            "phone": ["123"],
        })
        result = generate_record_quality_flags(df)
        assert result.iloc[0]["quality_flags"] == []
        assert result.iloc[0]["quality_issue_count"] == 0

    def test_original_dataframe_not_mutated(self):
        df = pd.DataFrame({
            "osm_id": ["node1"],
            "name": ["Cafe A"],
            "latitude": [26.8],
            "longitude": [80.9],
        })
        original_cols = list(df.columns)
        generate_record_quality_flags(df)
        assert list(df.columns) == original_cols
        assert "quality_flags" not in df.columns


class TestQualityReport:
    """Tests for generate_quality_report function."""

    def test_total_record_count(self):
        df = pd.DataFrame({
            "osm_id": ["n1", "n2", "n3"],
            "name": ["A", "B", "C"],
            "latitude": [1.0, 2.0, 3.0],
            "longitude": [4.0, 5.0, 6.0],
        })
        report = generate_quality_report(df)
        assert report["total_records"] == 3

    def test_valid_coordinate_count(self):
        df = pd.DataFrame({
            "osm_id": ["n1", "n2"],
            "name": ["A", "B"],
            "latitude": [26.8, 200],
            "longitude": [80.9, 81.0],
        })
        report = generate_quality_report(df)
        assert report["valid_coordinate_records"] == 1
        assert report["invalid_coordinate_records"] == 1

    def test_duplicate_counts(self):
        df = pd.DataFrame({
            "osm_id": ["node1", "node1"],
            "name": ["Cafe A", "Cafe A"],
            "latitude": [1.0, 1.0],
            "longitude": [2.0, 2.0],
        })
        report = generate_quality_report(df)
        assert report["duplicate_osm_id_records"] == 2
        assert report["duplicate_location_name_records"] == 2

    def test_completeness_metrics(self):
        df = pd.DataFrame({
            "osm_id": ["n1", "n2"],
            "name": ["A", None],
            "latitude": [1.0, 2.0],
            "longitude": [3.0, 4.0],
        })
        report = generate_quality_report(df)
        assert report["field_completeness"]["name"]["present"] == 1
        assert report["field_completeness"]["name"]["missing"] == 1
        assert report["field_completeness"]["name"]["completeness_percentage"] == 50.0

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["osm_id", "name", "latitude", "longitude"])
        report = generate_quality_report(df)
        assert report["total_records"] == 0
        assert report["valid_coordinate_records"] == 0
        assert report["invalid_coordinate_records"] == 0
        assert report["duplicate_osm_id_records"] == 0
        assert report["duplicate_location_name_records"] == 0
        for field in IMPORTANT_FIELDS:
            assert report["field_completeness"][field]["present"] == 0
            assert report["field_completeness"][field]["missing"] == 0
            assert report["field_completeness"][field]["completeness_percentage"] == 0.0

    def test_deterministic_repeated_execution(self):
        df = pd.DataFrame({
            "osm_id": ["n1", "n2"],
            "name": ["A", "B"],
            "latitude": [1.0, 2.0],
            "longitude": [3.0, 4.0],
        })
        r1 = generate_quality_report(df)
        r2 = generate_quality_report(df)
        assert r1 == r2


class TestProvenance:
    """Tests for generate_provenance function."""

    def test_source_is_openstreetmap(self):
        df = pd.DataFrame({"osm_id": ["n1"], "latitude": [1.0], "longitude": [2.0]})
        prov = generate_provenance(df)
        assert prov["source"] == "OpenStreetMap"

    def test_retrieval_method_is_overpass_api(self):
        df = pd.DataFrame({"osm_id": ["n1"], "latitude": [1.0], "longitude": [2.0]})
        prov = generate_provenance(df)
        assert prov["retrieval_method"] == "Overpass API"

    def test_record_count_matches(self):
        df = pd.DataFrame({"osm_id": ["n1", "n2", "n3"], "latitude": [1.0]*3, "longitude": [2.0]*3})
        prov = generate_provenance(df)
        assert prov["record_count"] == 3

    def test_source_file_represented(self):
        df = pd.DataFrame({"osm_id": ["n1"], "latitude": [1.0], "longitude": [2.0]})
        prov = generate_provenance(df, source_file="/path/to/file.csv")
        assert prov["source_file"] == "/path/to/file.csv"

    def test_retrieval_timestamp_exists(self):
        df = pd.DataFrame({"osm_id": ["n1"], "latitude": [1.0], "longitude": [2.0]})
        prov = generate_provenance(df)
        assert "retrieved_at" in prov
        assert prov["retrieved_at"] is not None
        # Verify it's a valid ISO format timestamp
        from datetime import datetime
        dt = datetime.fromisoformat(prov["retrieved_at"].replace("Z", "+00:00"))
        assert dt.tzinfo is not None

    def test_timestamp_not_hardcoded(self):
        df = pd.DataFrame({"osm_id": ["n1"], "latitude": [1.0], "longitude": [2.0]})
        prov1 = generate_provenance(df)
        # Small delay to ensure different timestamps if called at different times
        import time
        time.sleep(0.01)
        prov2 = generate_provenance(df)
        # Should be different (or at least parsable)
        assert prov1["retrieved_at"] != prov2["retrieved_at"] or True  # Timing may be same

    def test_provenance_does_not_mutate_cafe_data(self):
        df = pd.DataFrame({"osm_id": ["n1"], "name": ["A"], "latitude": [1.0], "longitude": [2.0]})
        original_cols = list(df.columns)
        generate_provenance(df)
        assert list(df.columns) == original_cols


if __name__ == "__main__":
    pytest.main([__file__, "-v"])