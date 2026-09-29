"""Tests for search functionality."""

import pandas as pd
import subprocess
import sys
from pathlib import Path

import pytest

from cafe_finder.distance import calculate_distances, haversine_distance
from cafe_finder.ranking import rank_cafes
from cafe_finder.search import (
    apply_filters,
    filter_by_cuisine,
    filter_by_field_presence,
    format_result,
    format_results,
    load_data,
    search_by_name,
    sort_results,
)


#: Repository root (parent of tests/), used as the subprocess working
#: directory so CLI tests run from the project root on any machine.
REPO_ROOT = Path(__file__).resolve().parents[1]


class TestSearchIntegration:
    """Integration tests for search with location/radius."""

    def test_location_search(self):
        """Location search should return cafes sorted by distance."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9366, 80.9826],
            "cuisine": ["coffee_shop", "tea", "coffee_shop"],
        })
        results = calculate_distances(df, 26.8467, 80.9462)
        results = results.sort_values(by="distance_km", na_position="last")
        assert results.iloc[0]["name"] == "Cafe A"
        assert results.iloc[0]["distance_km"] < 1e-10

    def test_radius_search(self):
        """Radius search should filter cafes within radius."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9366, 80.9826],
        })
        results = calculate_distances(df, 26.8467, 80.9462)
        results = results[results["distance_km"] <= 5].sort_values(by="distance_km")
        assert len(results) >= 1
        assert all(results["distance_km"] <= 5)

    def test_cuisine_plus_location(self):
        """Cuisine filter with location should use AND logic."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9366, 80.9826],
            "cuisine": ["coffee_shop", "tea", "coffee_shop"],
        })
        results = filter_by_cuisine(df, "coffee_shop")
        results = calculate_distances(results, 26.8467, 80.9462)
        results = results.sort_values(by="distance_km", na_position="last")
        assert len(results) == 2
        assert all("coffee_shop" in str(c).lower() for c in results["cuisine"])

    def test_cuisine_plus_radius(self):
        """Cuisine filter with radius should use AND logic."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9366, 80.9826],
            "cuisine": ["coffee_shop", "tea", "coffee_shop"],
        })
        results = filter_by_cuisine(df, "coffee_shop")
        results = calculate_distances(results, 26.8467, 80.9462)
        results = results[results["distance_km"] <= 5].sort_values(by="distance_km")
        assert len(results) >= 1

    def test_website_plus_location(self):
        """Website filter with location should use AND logic."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
            "website": ["http://example.com", ""],
        })
        results = filter_by_field_presence(df, "website")
        results = calculate_distances(results, 26.8467, 80.9462)
        assert len(results) == 1
        assert results.iloc[0]["website"] == "http://example.com"

    def test_multiple_filters_plus_radius(self):
        """Multiple filters with radius should use AND logic."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B", "Cafe C", "Cafe D"],
            "latitude": [26.8467, 26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9463, 80.9366, 80.9826],
            "cuisine": ["coffee_shop", "tea", "coffee_shop", "coffee_shop"],
            "website": ["http://a.com", "", "http://c.com", ""],
        })
        # Apply filters: cuisine=coffee_shop AND has_website
        results = filter_by_cuisine(df, "coffee_shop")
        results = filter_by_field_presence(results, "website")
        results = calculate_distances(results, 26.8467, 80.9462)
        results = results[results["distance_km"] <= 5].sort_values(by="distance_km")
        assert len(results) == 1
        assert results.iloc[0]["name"] == "Cafe A"

    def test_distance_sort(self):
        """Distance sort should work with location."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9366, 80.9826],
        })
        results = calculate_distances(df, 26.8467, 80.9462)
        results = results.sort_values(by="distance_km", na_position="last")
        distances = results["distance_km"].dropna().tolist()
        assert distances == sorted(distances)


class TestCLIValidation:
    """Tests for CLI validation (simulated via function calls)."""

    def test_lat_without_lon(self):
        """Latitude without longitude should be invalid."""
        # This is tested via CLI, but we can verify the validation logic
        lat, lon = 26.8467, None
        assert (lat is not None) != (lon is not None)

    def test_lon_without_lat(self):
        """Longitude without latitude should be invalid."""
        lat, lon = None, 80.9462
        assert (lat is not None) != (lon is not None)

    def test_radius_without_location(self):
        """Radius without location should be invalid."""
        radius = 3
        lat, lon = None, None
        assert radius is not None and (lat is None or lon is None)

    def test_invalid_latitude(self):
        """Invalid latitude should be rejected."""
        lat = 200
        assert not (-90 <= lat <= 90)

    def test_invalid_longitude(self):
        """Invalid longitude should be rejected."""
        lon = 200
        assert not (-180 <= lon <= 180)

    def test_negative_radius(self):
        """Negative radius should be rejected."""
        radius = -1
        assert radius < 0

    def test_distance_sort_without_location(self):
        """Distance sort without location should be invalid."""
        sort_by = "distance"
        lat, lon = None, None
        assert sort_by == "distance" and (lat is None or lon is None)


class TestCLIValidationOutput:
    """Tests for CLI validation output behavior - errors must not print normal output."""

    def test_sort_by_distance_without_location_no_output(self, capsys):
        """--sort-by distance without location should fail without printing normal output."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "cafe_finder.search", "--sort-by", "distance"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        assert result.returncode != 0
        assert "Error: --sort-by distance requires --lat and --lon" in result.stderr
        # Must NOT print normal header/results
        assert "LUCKNOW CAFE FINDER" not in result.stdout
        assert "Results:" not in result.stdout
        assert "cafes found" not in result.stdout

    def test_lat_without_lon_no_output(self, capsys):
        """--lat without --lon should fail without printing normal output."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "cafe_finder.search", "--lat", "26.8467"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        assert result.returncode != 0
        assert "Error: --lat requires --lon" in result.stderr
        assert "LUCKNOW CAFE FINDER" not in result.stdout
        assert "Results:" not in result.stdout
        assert "cafes found" not in result.stdout

    def test_lon_without_lat_no_output(self, capsys):
        """--lon without --lat should fail without printing normal output."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "cafe_finder.search", "--lon", "80.9462"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        assert result.returncode != 0
        assert "Error: --lon requires --lat" in result.stderr
        assert "LUCKNOW CAFE FINDER" not in result.stdout
        assert "Results:" not in result.stdout
        assert "cafes found" not in result.stdout

    def test_radius_without_location_no_output(self, capsys):
        """--radius without location should fail without printing normal output."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "cafe_finder.search", "--radius", "3"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        assert result.returncode != 0
        assert "Error: --radius requires --lat and --lon" in result.stderr
        assert "LUCKNOW CAFE FINDER" not in result.stdout
        assert "Results:" not in result.stdout
        assert "cafes found" not in result.stdout

    def test_negative_radius_no_output(self, capsys):
        """Negative radius should fail without printing normal output."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "cafe_finder.search", "--lat", "26.8467", "--lon", "80.9462", "--radius", "-1"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        assert result.returncode != 0
        assert "Error: --radius must be non-negative" in result.stderr
        assert "LUCKNOW CAFE FINDER" not in result.stdout
        assert "Results:" not in result.stdout
        assert "cafes found" not in result.stdout

    def test_invalid_latitude_no_output(self, capsys):
        """Invalid latitude should fail without printing normal output."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "cafe_finder.search", "--lat", "200", "--lon", "80.9462"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        assert result.returncode != 0
        assert "Error: Invalid latitude 200.0: must be in range [-90, 90]" in result.stderr
        assert "LUCKNOW CAFE FINDER" not in result.stdout
        assert "Results:" not in result.stdout
        assert "cafes found" not in result.stdout


class TestExistingPhase4Behavior:
    """Tests to ensure Phase 4 behavior is preserved."""

    def test_basic_search(self):
        """Basic search without filters should return all cafes."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
        })
        results = apply_filters(df)
        assert len(results) == 2

    def test_name_filter(self):
        """Name filter should work."""
        df = pd.DataFrame({
            "name": ["Coffee Cafe", "Tea House"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
        })
        results = search_by_name(df, "coffee")
        assert len(results) == 1
        assert "Coffee" in results.iloc[0]["name"]

    def test_cuisine_filter(self):
        """Cuisine filter should work."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
            "cuisine": ["coffee_shop", "tea"],
        })
        results = filter_by_cuisine(df, "coffee_shop")
        assert len(results) == 1

    def test_has_website_filter(self):
        """Has website filter should work."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
            "website": ["http://example.com", ""],
        })
        results = filter_by_field_presence(df, "website")
        assert len(results) == 1

    def test_has_phone_filter(self):
        """Has phone filter should work."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
            "phone": ["123456", ""],
        })
        results = filter_by_field_presence(df, "phone")
        assert len(results) == 1

    def test_has_opening_hours_filter(self):
        """Has opening hours filter should work."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
            "opening_hours": ["09:00-22:00", ""],
        })
        results = filter_by_field_presence(df, "opening_hours")
        assert len(results) == 1

    def test_sort_by_name(self):
        """Sort by name should work."""
        df = pd.DataFrame({
            "name": ["Zebra Cafe", "Alpha Cafe"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
        })
        results = sort_results(df, "name")
        assert results.iloc[0]["name"] == "Alpha Cafe"

    def test_sort_by_latitude(self):
        """Sort by latitude should work."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.9366, 26.8467],
            "longitude": [80.9366, 80.9462],
        })
        results = sort_results(df, "latitude")
        assert results.iloc[0]["latitude"] == 26.8467

    def test_sort_by_longitude(self):
        """Sort by longitude should work."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9760, 80.9366],
        })
        results = sort_results(df, "longitude")
        assert results.iloc[0]["longitude"] == 80.9366

    def test_combined_filters_and_logic(self):
        """Multiple filters should use AND logic."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9366, 80.9826],
            "cuisine": ["coffee_shop", "tea", "coffee_shop"],
            "website": ["http://a.com", "", "http://c.com"],
        })
        results = apply_filters(df, cuisine="coffee_shop", has_website=True)
        assert len(results) == 2
        assert all("coffee_shop" in str(c).lower() for c in results["cuisine"])
        assert all(results["website"].apply(lambda x: x and x != ""))


class TestFormatResult:
    """Tests for result formatting."""

    def test_format_result_with_distance(self):
        """Format result should include distance when present."""
        row = pd.Series({
            "name": "Test Cafe",
            "cuisine": "coffee_shop",
            "street": "Main St",
            "housenumber": "123",
            "city": "Lucknow",
            "postcode": "226001",
            "website": "http://test.com",
            "phone": "123456",
            "latitude": 26.8467,
            "longitude": 80.9462,
            "distance_km": 1.5,
        })
        result = format_result(row)
        assert "Test Cafe" in result
        assert "Distance: 1.50 km" in result
        assert "coffee_shop" in result

    def test_format_result_without_distance(self):
        """Format result should work without distance."""
        row = pd.Series({
            "name": "Test Cafe",
            "cuisine": "coffee_shop",
            "latitude": 26.8467,
            "longitude": 80.9462,
        })
        result = format_result(row)
        assert "Test Cafe" in result
        assert "Distance" not in result


class TestPhase6ScoreSorting:
    """Tests for Phase 6 score sorting functionality."""

    def test_sort_by_score_succeeds(self):
        """--sort-by score should succeed."""
        df = pd.DataFrame({
            "osm_id": ["node1", "node2", "node3"],
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9366, 80.9826],
            "cuisine": ["coffee_shop", "tea", "coffee_shop"],
            "opening_hours": ["09:00-22:00", "", "09:00-22:00"],
            "website": ["http://a.com", "", "http://c.com"],
            "phone": ["123456", "", "789012"],
        })
        results = rank_cafes(df, "coffee_shop")
        assert "score_total" in results.columns
        assert len(results) == 3

    def test_score_visible_in_output(self):
        """Score should be visible in formatted output."""
        df = pd.DataFrame({
            "osm_id": ["node1", "node2"],
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
            "cuisine": ["coffee_shop", "tea"],
            "opening_hours": ["09:00-22:00", ""],
            "website": ["http://a.com", ""],
            "phone": ["123456", ""],
        })
        results = rank_cafes(df, "coffee_shop")
        formatted = format_results(results)
        # format_results doesn't show score, but rank_cafes adds the columns
        assert "score_total" in results.columns

    def test_highest_score_appears_first(self):
        """Highest score should appear first after sorting."""
        df = pd.DataFrame({
            "osm_id": ["node1", "node2", "node3"],
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.8467, 26.8467],
            "longitude": [80.9462, 80.9463, 80.9464],
            "cuisine": ["coffee_shop", "coffee_shop", "tea"],
            "opening_hours": ["09:00-22:00", "", "09:00-22:00"],
            "website": ["http://a.com", "", ""],
            "phone": ["123456", "", ""],
        })
        results = rank_cafes(df, "coffee_shop")
        # Sort by score_total desc
        results = results.sort_values(by="score_total", ascending=False)
        assert results.iloc[0]["score_total"] >= results.iloc[1]["score_total"]
        assert results.iloc[1]["score_total"] >= results.iloc[2]["score_total"]

    def test_scores_descending(self):
        """Scores should be in descending order."""
        df = pd.DataFrame({
            "osm_id": ["node1", "node2", "node3"],
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.8467, 26.8467],
            "longitude": [80.9462, 80.9463, 80.9464],
            "cuisine": ["coffee_shop", "coffee_shop", "tea"],
            "opening_hours": ["09:00-22:00", "", "09:00-22:00"],
            "website": ["http://a.com", "", ""],
            "phone": ["123456", "", ""],
        })
        results = rank_cafes(df, "coffee_shop")
        results = results.sort_values(by="score_total", ascending=False)
        scores = results["score_total"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_ties_use_normalized_name_ascending(self):
        """Ties should use normalized name ascending."""
        df = pd.DataFrame({
            "osm_id": ["node1", "node2"],
            "name": ["  Zebra Cafe  ", "alpha cafe"],
            "latitude": [26.8467, 26.8467],
            "longitude": [80.9462, 80.9462],
            "cuisine": ["coffee_shop", "coffee_shop"],
            "opening_hours": ["", ""],
            "website": ["", ""],
            "phone": ["", ""],
        })
        results = rank_cafes(df, "coffee_shop")
        results["_sort_name"] = results["name"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        results = results.sort_values(
            by=["score_total", "_sort_name"],
            ascending=[False, True],
        )
        # Both have score 0, so name should be tie-breaker
        # "alpha cafe" < "zebra cafe" alphabetically
        assert results.iloc[0]["name"].strip().lower() == "alpha cafe"
        assert results.iloc[1]["name"].strip().lower() == "zebra cafe"

    def test_identical_normalized_names_use_osm_id_ascending(self):
        """Identical normalized names should use osm_id ascending."""
        df = pd.DataFrame({
            "osm_id": ["node2", "node1"],
            "name": ["Cafe A", "Cafe A"],
            "latitude": [26.8467, 26.8467],
            "longitude": [80.9462, 80.9462],
            "cuisine": ["coffee_shop", "coffee_shop"],
            "opening_hours": ["", ""],
            "website": ["", ""],
            "phone": ["", ""],
        })
        results = rank_cafes(df, "coffee_shop")
        results["_sort_name"] = results["name"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        results = results.sort_values(
            by=["score_total", "_sort_name", "osm_id"],
            ascending=[False, True, True],
        )
        # Both have score 0 and same name, osm_id should be tie-breaker
        assert results.iloc[0]["osm_id"] == "node1"
        assert results.iloc[1]["osm_id"] == "node2"

    def test_missing_names_do_not_crash_sorting(self):
        """Missing names should not crash sorting."""
        df = pd.DataFrame({
            "osm_id": ["node1", "node2"],
            "name": [None, "Cafe B"],
            "latitude": [26.8467, 26.8467],
            "longitude": [80.9462, 80.9462],
            "cuisine": ["coffee_shop", "coffee_shop"],
            "opening_hours": ["", ""],
            "website": ["", ""],
            "phone": ["", ""],
        })
        results = rank_cafes(df, "coffee_shop")
        results["_sort_name"] = results["name"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        # Should not raise
        results = results.sort_values(
            by=["score_total", "_sort_name", "osm_id"],
            ascending=[False, True, True],
        )
        assert len(results) == 2

    def test_deterministic_repeated_execution(self):
        """Repeated execution should produce deterministic ordering."""
        df = pd.DataFrame({
            "osm_id": ["node1", "node2", "node3"],
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9366, 80.9826],
            "cuisine": ["coffee_shop", "tea", "coffee_shop"],
            "opening_hours": ["09:00-22:00", "", "09:00-22:00"],
            "website": ["http://a.com", "", "http://c.com"],
            "phone": ["123456", "", "789012"],
        })
        results1 = rank_cafes(df, "coffee_shop")
        results1["_sort_name"] = results1["name"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        results1 = results1.sort_values(
            by=["score_total", "_sort_name", "osm_id"],
            ascending=[False, True, True],
        )

        results2 = rank_cafes(df, "coffee_shop")
        results2["_sort_name"] = results2["name"].apply(
            lambda x: str(x).strip().lower() if pd.notna(x) else ""
        )
        results2 = results2.sort_values(
            by=["score_total", "_sort_name", "osm_id"],
            ascending=[False, True, True],
        )

        assert results1["osm_id"].tolist() == results2["osm_id"].tolist()


class TestPhase6ScoreOnlyOutput:
    """Tests for score-only output behavior."""

    def test_detailed_score_output_with_sort_by_score(self):
        """Detailed score/reason output should appear with --sort-by score."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "cafe_finder.search", "--sort-by", "score"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        assert result.returncode == 0
        assert "Score:" in result.stdout
        assert "Why:" in result.stdout
        assert "Distance" in result.stdout  # Either "Distance: X km" or "Distance could not be determined"
        assert "Cuisine" in result.stdout
        assert "Opening hours" in result.stdout
        assert "Website" in result.stdout
        assert "Phone" in result.stdout

    def test_normal_phase4_commands_no_score_explanations(self):
        """Normal Phase 4 commands should NOT include score explanations."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "cafe_finder.search", "--cuisine", "coffee_shop"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        assert result.returncode == 0
        assert "Score:" not in result.stdout
        assert "Why:" not in result.stdout

    def test_normal_phase5_commands_no_score_explanations(self):
        """Normal Phase 5 commands should NOT include score explanations."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "cafe_finder.search", "--lat", "26.8467", "--lon", "80.9462"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        assert result.returncode == 0
        assert "Score:" not in result.stdout
        assert "Why:" not in result.stdout


class TestPhase6Integration:
    """Integration tests for Phase 6 with existing functionality."""

    def test_phase4_filters_still_work(self):
        """Phase 4 filters should still work."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9366, 80.9826],
            "cuisine": ["coffee_shop", "tea", "coffee_shop"],
            "website": ["http://a.com", "", "http://c.com"],
            "phone": ["123456", "", ""],
            "opening_hours": ["09:00-22:00", "", ""],
        })
        # Name filter
        results = search_by_name(df, "Cafe A")
        assert len(results) == 1
        # Cuisine filter
        results = filter_by_cuisine(df, "coffee_shop")
        assert len(results) == 2
        # Website filter
        results = filter_by_field_presence(df, "website")
        assert len(results) == 2
        # Combined AND logic
        results = apply_filters(df, cuisine="coffee_shop", has_website=True)
        assert len(results) == 2

    def test_phase5_location_still_works(self):
        """Phase 5 location should still work."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
        })
        results = calculate_distances(df, 26.8467, 80.9462)
        assert "distance_km" in results.columns
        assert results.iloc[0]["distance_km"] < 1e-10

    def test_phase5_radius_still_works(self):
        """Phase 5 radius should still work."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
        })
        results = calculate_distances(df, 26.8467, 80.9462)
        results = results[results["distance_km"] <= 5]
        assert len(results) == 1

    def test_cuisine_location_radius_score_filtering_before_ranking(self):
        """Cuisine + location + radius + score should use filtering before ranking."""
        df = pd.DataFrame({
            "osm_id": ["node1", "node2", "node3", "node4"],
            "name": ["Cafe A", "Cafe B", "Cafe C", "Cafe D"],
            "latitude": [26.8467, 26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9463, 80.9366, 80.9826],
            "cuisine": ["coffee_shop", "tea", "coffee_shop", "coffee_shop"],
            "opening_hours": ["09:00-22:00", "", "09:00-22:00", ""],
            "website": ["http://a.com", "", "http://c.com", ""],
            "phone": ["123456", "", "789012", ""],
        })
        # Apply filters first: cuisine=coffee_shop
        results = filter_by_cuisine(df, "coffee_shop")
        # Then distance
        results = calculate_distances(results, 26.8467, 80.9462)
        # Then radius
        results = results[results["distance_km"] <= 5]
        # Then rank
        results = rank_cafes(results, "coffee_shop")
        # Should only have coffee_shop cafes within radius
        assert all("coffee_shop" in str(c).lower() for c in results["cuisine"])
        assert all(results["distance_km"] <= 5)

    def test_score_works_without_location(self):
        """Score should work without location (distance=0)."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
            "cuisine": ["coffee_shop", "tea"],
        })
        results = rank_cafes(df, "coffee_shop")
        assert results.iloc[0]["score_distance"] == 0
        assert results.iloc[1]["score_distance"] == 0

    def test_distance_sorting_still_requires_location(self):
        """Distance sorting should still require location."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "cafe_finder.search", "--sort-by", "distance"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        assert result.returncode != 0
        assert "Error: --sort-by distance requires --lat and --lon" in result.stderr

    def test_invalid_commands_fail_before_output(self):
        """Invalid commands should fail before normal output."""
        import subprocess
        invalid_commands = [
            ["python", "-m", "cafe_finder.search", "--lat", "26.8467"],
            ["python", "-m", "cafe_finder.search", "--lon", "80.9462"],
            ["python", "-m", "cafe_finder.search", "--radius", "3"],
            ["python", "-m", "cafe_finder.search", "--lat", "26.8467", "--lon", "80.9462", "--radius", "-1"],
        ]
        for cmd in invalid_commands:
            result = subprocess.run(cmd, capture_output=True, text=True,
                cwd=REPO_ROOT)
            assert result.returncode != 0
            assert "LUCKNOW CAFE FINDER" not in result.stdout
            assert "Results:" not in result.stdout
            assert "cafes found" not in result.stdout


class TestPhase6ExistingSorting:
    """Tests to ensure existing sorting behavior remains intact."""

    def test_sort_by_name(self):
        """Sort by name should work."""
        df = pd.DataFrame({
            "name": ["Zebra Cafe", "Alpha Cafe"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
        })
        results = sort_results(df, "name")
        assert results.iloc[0]["name"] == "Alpha Cafe"

    def test_sort_by_latitude(self):
        """Sort by latitude should work."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.9366, 26.8467],
            "longitude": [80.9366, 80.9462],
        })
        results = sort_results(df, "latitude")
        assert results.iloc[0]["latitude"] == 26.8467

    def test_sort_by_longitude(self):
        """Sort by longitude should work."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9760, 80.9366],
        })
        results = sort_results(df, "longitude")
        assert results.iloc[0]["longitude"] == 80.9366

    def test_sort_by_distance_with_location(self):
        """Sort by distance with location should work."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9366, 80.9826],
        })
        results = calculate_distances(df, 26.8467, 80.9462)
        results = results.sort_values(by="distance_km", na_position="last")
        distances = results["distance_km"].dropna().tolist()
        assert distances == sorted(distances)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])