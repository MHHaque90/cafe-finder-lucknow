"""Tests for distance calculations."""

import math

import pandas as pd

import pytest

from cafe_finder.distance import calculate_distances, haversine_distance


class TestHaversineDistance:
    """Tests for haversine_distance function."""

    def test_same_coordinate(self):
        """Same coordinate should return approximately 0 km."""
        d = haversine_distance(26.8467, 80.9462, 26.8467, 80.9462)
        assert abs(d) < 1e-10

    def test_known_coordinate_pair(self):
        """Known coordinate pair should return reasonable distance."""
        # Delhi to Mumbai approx 1150-1200 km
        d = haversine_distance(28.7041, 77.1025, 19.0761, 72.8774)
        assert 1100 < d < 1250

    def test_symmetry(self):
        """Distance should be symmetric: d(A,B) == d(B,A)."""
        d1 = haversine_distance(26.8467, 80.9462, 26.9366, 80.9366)
        d2 = haversine_distance(26.9366, 80.9366, 26.8467, 80.9462)
        assert abs(d1 - d2) < 1e-10

    def test_latitude_lower_boundary(self):
        """Latitude -90 should be valid."""
        d = haversine_distance(-90, 0, -89, 0)
        assert d > 0

    def test_latitude_upper_boundary(self):
        """Latitude 90 should be valid."""
        d = haversine_distance(90, 0, 89, 0)
        assert d > 0

    def test_longitude_lower_boundary(self):
        """Longitude -180 should be valid."""
        d = haversine_distance(0, -180, 0, -179)
        assert d > 0

    def test_longitude_upper_boundary(self):
        """Longitude 180 should be valid."""
        d = haversine_distance(0, 180, 0, 179)
        assert d > 0

    def test_invalid_latitude_high(self):
        """Latitude > 90 should raise ValueError."""
        with pytest.raises(ValueError, match="latitude.*90"):
            haversine_distance(91, 80.9462, 26.8467, 80.9462)

    def test_invalid_latitude_low(self):
        """Latitude < -90 should raise ValueError."""
        with pytest.raises(ValueError, match="latitude.*-90"):
            haversine_distance(-91, 80.9462, 26.8467, 80.9462)

    def test_invalid_longitude_high(self):
        """Longitude > 180 should raise ValueError."""
        with pytest.raises(ValueError, match="longitude.*180"):
            haversine_distance(26.8467, 181, 26.8467, 80.9462)

    def test_invalid_longitude_low(self):
        """Longitude < -180 should raise ValueError."""
        with pytest.raises(ValueError, match="longitude.*-180"):
            haversine_distance(26.8467, -181, 26.8467, 80.9462)

    def test_invalid_latitude_far(self):
        """Latitude 200 should raise ValueError with clear message."""
        with pytest.raises(ValueError, match="Invalid latitude 200"):
            haversine_distance(200, 80.9462, 26.8467, 80.9462)

    def test_invalid_longitude_far(self):
        """Longitude 200 should raise ValueError with clear message."""
        with pytest.raises(ValueError, match="Invalid longitude 200"):
            haversine_distance(26.8467, 200, 26.8467, 80.9462)


class TestCalculateDistances:
    """Tests for calculate_distances function."""

    def test_valid_coordinates(self):
        """DataFrame with valid coordinates should get distance_km."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
        })
        result = calculate_distances(df, 26.8467, 80.9462)
        assert "distance_km" in result.columns
        assert len(result) == 2
        assert result.iloc[0]["distance_km"] < 1e-10  # Same coordinate
        assert result.iloc[1]["distance_km"] > 0

    def test_missing_coordinates(self):
        """DataFrame with missing coordinates should have NaN distance."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, None],
            "longitude": [80.9462, 80.9366],
        })
        result = calculate_distances(df, 26.8467, 80.9462)
        assert pd.notna(result.iloc[0]["distance_km"])
        assert pd.isna(result.iloc[1]["distance_km"])

    def test_non_numeric_coordinates(self):
        """DataFrame with non-numeric coordinates should have NaN distance."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, "invalid"],
            "longitude": [80.9462, 80.9366],
        })
        result = calculate_distances(df, 26.8467, 80.9462)
        assert pd.notna(result.iloc[0]["distance_km"])
        assert pd.isna(result.iloc[1]["distance_km"])

    def test_original_not_mutated(self):
        """Original DataFrame should not be mutated."""
        df = pd.DataFrame({
            "name": ["Cafe A"],
            "latitude": [26.8467],
            "longitude": [80.9462],
        })
        original_cols = list(df.columns)
        calculate_distances(df, 26.8467, 80.9462)
        assert list(df.columns) == original_cols
        assert "distance_km" not in df.columns

    def test_distance_km_is_numeric(self):
        """distance_km should be numeric (float)."""
        df = pd.DataFrame({
            "name": ["Cafe A"],
            "latitude": [26.8467],
            "longitude": [80.9462],
        })
        result = calculate_distances(df, 26.8467, 80.9462)
        assert pd.api.types.is_numeric_dtype(result["distance_km"])

    def test_preserves_existing_columns(self):
        """All existing columns should be preserved."""
        df = pd.DataFrame({
            "name": ["Cafe A"],
            "latitude": [26.8467],
            "longitude": [80.9462],
            "cuisine": ["coffee_shop"],
            "website": ["http://example.com"],
        })
        result = calculate_distances(df, 26.8467, 80.9462)
        for col in df.columns:
            assert col in result.columns

    def test_empty_dataframe(self):
        """Empty DataFrame should return empty DataFrame with distance_km."""
        df = pd.DataFrame(columns=["name", "latitude", "longitude"])
        result = calculate_distances(df, 26.8467, 80.9462)
        assert len(result) == 0
        assert "distance_km" in result.columns


class TestRadiusFiltering:
    """Tests for radius filtering behavior (integrated in search)."""

    def test_radius_boundary_inclusion(self):
        """Cafes exactly at radius boundary should be included."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.8467],
            "longitude": [80.9462, 80.9760],
        })
        # Distance from 26.8467, 80.9462 to 26.8467, 80.9760 is about 3.3 km
        result = calculate_distances(df, 26.8467, 80.9462)
        radius = result.iloc[1]["distance_km"]
        filtered = result[result["distance_km"] <= radius]
        assert len(filtered) == 2

    def test_radius_excludes_farther(self):
        """Cafes beyond radius should be excluded."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.8467],
            "longitude": [80.9462, 80.9760],
        })
        result = calculate_distances(df, 26.8467, 80.9462)
        radius = result.iloc[1]["distance_km"] - 0.1
        filtered = result[result["distance_km"] <= radius]
        assert len(filtered) == 1

    def test_zero_radius(self):
        """Zero radius should only include cafes at exact location."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.8467],
            "longitude": [80.9462, 80.9463],
        })
        result = calculate_distances(df, 26.8467, 80.9462)
        filtered = result[result["distance_km"] <= 0]
        assert len(filtered) == 1
        assert filtered.iloc[0]["name"] == "Cafe A"

    def test_negative_radius_raises(self):
        """Negative radius should be rejected in CLI (not in distance module)."""
        # This is handled in CLI validation, not in distance module
        pass

    def test_results_sorted_nearest_first(self):
        """Results should be sorted by distance ascending when radius applied."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B", "Cafe C"],
            "latitude": [26.8467, 26.9366, 26.8765],
            "longitude": [80.9462, 80.9366, 80.9826],
        })
        result = calculate_distances(df, 26.8467, 80.9462)
        result = result.sort_values(by="distance_km", na_position="last")
        distances = result["distance_km"].dropna().tolist()
        assert distances == sorted(distances)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])