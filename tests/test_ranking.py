"""Tests for ranking functionality (Phase 6)."""

import pandas as pd
import pytest

from cafe_finder.ranking import (
    MAX_TOTAL_SCORE,
    calculate_distance_score,
    calculate_cuisine_score,
    calculate_opening_hours_score,
    calculate_website_score,
    calculate_phone_score,
    score_cafe,
    rank_cafes,
)


class TestDistanceScoring:
    """Tests for calculate_distance_score function."""

    def test_zero_km(self):
        """0 km should give 40 points."""
        assert calculate_distance_score(0) == 40

    def test_exactly_1_km(self):
        """Exactly 1 km should give 40 points."""
        assert calculate_distance_score(1) == 40

    def test_1_to_2_km(self):
        """Between 1 and 2 km should give 30 points."""
        assert calculate_distance_score(1.5) == 30
        assert calculate_distance_score(2) == 30

    def test_2_to_3_km(self):
        """Between 2 and 3 km should give 20 points."""
        assert calculate_distance_score(2.5) == 20
        assert calculate_distance_score(3) == 20

    def test_3_to_5_km(self):
        """Between 3 and 5 km should give 10 points."""
        assert calculate_distance_score(4) == 10
        assert calculate_distance_score(5) == 10

    def test_over_5_km(self):
        """Over 5 km should give 0 points."""
        assert calculate_distance_score(5.1) == 0
        assert calculate_distance_score(10) == 0
        assert calculate_distance_score(100) == 0

    def test_missing_distance(self):
        """Missing distance should give 0 points."""
        assert calculate_distance_score(None) == 0

    def test_invalid_distance(self):
        """Invalid distance should give 0 points."""
        assert calculate_distance_score("invalid") == 0
        assert calculate_distance_score(float("nan")) == 0


class TestCuisineScoring:
    """Tests for calculate_cuisine_score function."""

    def test_exact_match(self):
        """Exact tag match should give 30 points."""
        assert calculate_cuisine_score("coffee_shop", "coffee_shop") == 30

    def test_case_insensitive_match(self):
        """Case-insensitive exact match should give 30 points."""
        assert calculate_cuisine_score("COFFEE_SHOP", "coffee_shop") == 30
        assert calculate_cuisine_score("Coffee_Shop", "COFFEE_SHOP") == 30

    def test_semicolon_separated_exact_tag(self):
        """Semicolon-separated tags with exact match should give 30 points."""
        assert calculate_cuisine_score("coffee_shop;pasta", "coffee_shop") == 30
        assert calculate_cuisine_score("pasta;coffee_shop", "coffee_shop") == 30
        assert calculate_cuisine_score("tea;coffee_shop;pasta", "coffee_shop") == 30

    def test_partial_non_exact_match(self):
        """Partial/non-exact match should give 0 points."""
        assert calculate_cuisine_score("coffee_shop", "coffee") == 0
        assert calculate_cuisine_score("coffee", "coffee_shop") == 0
        assert calculate_cuisine_score("coffee_shop;pasta", "shop") == 0

    def test_missing_cuisine(self):
        """Missing cuisine should give 0 points."""
        assert calculate_cuisine_score(None, "coffee_shop") == 0
        assert calculate_cuisine_score("", "coffee_shop") == 0
        assert calculate_cuisine_score("   ", "coffee_shop") == 0

    def test_no_requested_cuisine(self):
        """No requested cuisine should give 0 points."""
        assert calculate_cuisine_score("coffee_shop", None) == 0
        assert calculate_cuisine_score("coffee_shop", "") == 0
        assert calculate_cuisine_score("coffee_shop", "   ") == 0


class TestMetadataScoring:
    """Tests for metadata scoring functions."""

    def test_opening_hours_present(self):
        """Opening hours present should give 15 points."""
        assert calculate_opening_hours_score("09:00-22:00") == 15
        assert calculate_opening_hours_score("Mo-Fr 08:00-18:00") == 15

    def test_opening_hours_missing(self):
        """Opening hours missing should give 0 points."""
        assert calculate_opening_hours_score(None) == 0
        assert calculate_opening_hours_score("") == 0
        assert calculate_opening_hours_score("   ") == 0
        assert calculate_opening_hours_score(float("nan")) == 0

    def test_website_present(self):
        """Website present should give 10 points."""
        assert calculate_website_score("http://example.com") == 10
        assert calculate_website_score("https://site.com") == 10

    def test_website_missing(self):
        """Website missing should give 0 points."""
        assert calculate_website_score(None) == 0
        assert calculate_website_score("") == 0
        assert calculate_website_score("   ") == 0
        assert calculate_website_score(float("nan")) == 0

    def test_phone_present(self):
        """Phone present should give 5 points."""
        assert calculate_phone_score("1234567890") == 5
        assert calculate_phone_score("+91 1234567890") == 5

    def test_phone_missing(self):
        """Phone missing should give 0 points."""
        assert calculate_phone_score(None) == 0
        assert calculate_phone_score("") == 0
        assert calculate_phone_score("   ") == 0
        assert calculate_phone_score(float("nan")) == 0


class TestScoreCafe:
    """Tests for score_cafe function."""

    def test_all_components_present(self):
        """All five score components should exist."""
        row = pd.Series({
            "distance_km": 0.5,
            "cuisine": "coffee_shop",
            "opening_hours": "09:00-22:00",
            "website": "http://example.com",
            "phone": "123456",
        })
        result = score_cafe(row, "coffee_shop")
        assert "score_distance" in result
        assert "score_cuisine" in result
        assert "score_opening_hours" in result
        assert "score_website" in result
        assert "score_phone" in result
        assert "score_total" in result
        assert "reasons" in result

    def test_total_exists(self):
        """Total score should exist and be sum of components."""
        row = pd.Series({
            "distance_km": 0.5,
            "cuisine": "coffee_shop",
            "opening_hours": "09:00-22:00",
            "website": "http://example.com",
            "phone": "123456",
        })
        result = score_cafe(row, "coffee_shop")
        expected = 40 + 30 + 15 + 10 + 5
        assert result["score_total"] == expected

    def test_reasons_correspond_to_scores(self):
        """Reasons should correspond to component scores."""
        row = pd.Series({
            "distance_km": 0.5,
            "cuisine": "coffee_shop",
            "opening_hours": "09:00-22:00",
            "website": "http://example.com",
            "phone": "123456",
        })
        result = score_cafe(row, "coffee_shop")
        reasons = result["reasons"]
        assert any("40 points" in r and "Distance" in r for r in reasons)
        assert any("30 points" in r and "Cuisine match" in r for r in reasons)
        assert any("15 points" in r and "Opening hours available" in r for r in reasons)
        assert any("10 points" in r and "Website available" in r for r in reasons)
        assert any("5 points" in r and "Phone available" in r for r in reasons)

    def test_missing_information_dataset_language(self):
        """Missing info should be described as unavailable in dataset."""
        row = pd.Series({
            "distance_km": None,
            "cuisine": None,
            "opening_hours": None,
            "website": None,
            "phone": None,
        })
        result = score_cafe(row, "coffee_shop")
        reasons = result["reasons"]
        assert any("could not be determined from dataset" in r for r in reasons)
        assert any("unavailable in dataset" in r for r in reasons)
        assert not any("cafe has no" in r for r in reasons)
        assert not any("does not have" in r for r in reasons)

    def test_no_unsupported_claims(self):
        """No unsupported real-world claims."""
        row = pd.Series({
            "distance_km": None,
            "cuisine": "coffee_shop",
            "opening_hours": None,
            "website": None,
            "phone": None,
        })
        result = score_cafe(row, "coffee_shop")
        reasons = result["reasons"]
        for reason in reasons:
            assert "doesn't have" not in reason.lower()
            assert "does not have" not in reason.lower()
            assert "lacks" not in reason.lower()

    def test_max_score_100(self):
        """Maximum score should be 100."""
        row = pd.Series({
            "distance_km": 0.5,
            "cuisine": "coffee_shop",
            "opening_hours": "09:00-22:00",
            "website": "http://example.com",
            "phone": "123456",
        })
        result = score_cafe(row, "coffee_shop")
        assert result["score_total"] == 100
        assert result["score_total"] <= MAX_TOTAL_SCORE

    def test_min_score_0(self):
        """Minimum score should be 0."""
        row = pd.Series({
            "distance_km": None,
            "cuisine": None,
            "opening_hours": None,
            "website": None,
            "phone": None,
        })
        result = score_cafe(row, None)
        assert result["score_total"] == 0
        assert result["score_total"] >= 0

    def test_no_negative_scores(self):
        """No negative scores."""
        row = pd.Series({
            "distance_km": 10,
            "cuisine": "tea",
            "opening_hours": None,
            "website": None,
            "phone": None,
        })
        result = score_cafe(row, "coffee_shop")
        assert result["score_total"] >= 0
        assert result["score_distance"] >= 0
        assert result["score_cuisine"] >= 0
        assert result["score_opening_hours"] >= 0
        assert result["score_website"] >= 0
        assert result["score_phone"] >= 0

    def test_deterministic_repeated_calculation(self):
        """Repeated calculation should produce identical results."""
        row = pd.Series({
            "distance_km": 1.5,
            "cuisine": "coffee_shop;pasta",
            "opening_hours": "09:00-22:00",
            "website": "http://example.com",
            "phone": "123456",
        })
        results = [score_cafe(row, "coffee_shop") for _ in range(10)]
        for r in results[1:]:
            assert r == results[0]


class TestRankCafes:
    """Tests for rank_cafes function."""

    def test_original_dataframe_unchanged(self):
        """Original DataFrame should not be mutated."""
        df = pd.DataFrame({
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
            "cuisine": ["coffee_shop", "tea"],
        })
        original_cols = list(df.columns)
        result = rank_cafes(df, "coffee_shop")
        assert list(df.columns) == original_cols
        for col in ["score_total", "score_distance", "score_cuisine",
                    "score_opening_hours", "score_website", "score_phone", "score_reasons"]:
            assert col not in df.columns

    def test_score_columns_added(self):
        """Score columns should be added to result."""
        df = pd.DataFrame({
            "name": ["Cafe A"],
            "latitude": [26.8467],
            "longitude": [80.9462],
            "cuisine": ["coffee_shop"],
        })
        result = rank_cafes(df, "coffee_shop")
        for col in ["score_total", "score_distance", "score_cuisine",
                    "score_opening_hours", "score_website", "score_phone", "score_reasons"]:
            assert col in result.columns

    def test_empty_dataframe_works(self):
        """Empty DataFrame should work."""
        df = pd.DataFrame(columns=["name", "latitude", "longitude", "cuisine"])
        result = rank_cafes(df, "coffee_shop")
        assert len(result) == 0
        for col in ["score_total", "score_distance", "score_cuisine",
                    "score_opening_hours", "score_website", "score_phone", "score_reasons"]:
            assert col in result.columns

    def test_missing_values_work(self):
        """Missing values should be handled gracefully."""
        df = pd.DataFrame({
            "name": ["Cafe A"],
            "latitude": [None],
            "longitude": [None],
            "cuisine": [None],
            "opening_hours": [None],
            "website": [None],
            "phone": [None],
        })
        result = rank_cafes(df, "coffee_shop")
        assert len(result) == 1
        assert result.iloc[0]["score_total"] == 0

    def test_missing_distance_works(self):
        """Missing distance_km should be handled gracefully."""
        df = pd.DataFrame({
            "name": ["Cafe A"],
            "latitude": [26.8467],
            "longitude": [80.9462],
            "cuisine": ["coffee_shop"],
        })
        result = rank_cafes(df, "coffee_shop")
        assert result.iloc[0]["score_distance"] == 0

    def test_does_not_sort_dataframe(self):
        """rank_cafes should NOT sort the DataFrame."""
        df = pd.DataFrame({
            "name": ["Zebra Cafe", "Alpha Cafe"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
            "cuisine": ["coffee_shop", "coffee_shop"],
        })
        result = rank_cafes(df, "coffee_shop")
        # Input order: Zebra Cafe, Alpha Cafe
        # If not sorted, output should preserve this order
        assert result.iloc[0]["name"] == "Zebra Cafe"
        assert result.iloc[1]["name"] == "Alpha Cafe"

    def test_preserves_all_original_columns(self):
        """All original columns should be preserved."""
        df = pd.DataFrame({
            "osm_id": ["node1", "node2"],
            "name": ["Cafe A", "Cafe B"],
            "latitude": [26.8467, 26.9366],
            "longitude": [80.9462, 80.9366],
            "street": ["Main St", "Second St"],
            "housenumber": ["123", "456"],
            "city": ["Lucknow", "Lucknow"],
            "postcode": ["226001", "226002"],
            "cuisine": ["coffee_shop", "tea"],
            "opening_hours": ["09:00-22:00", ""],
            "website": ["http://a.com", ""],
            "phone": ["123456", ""],
            "source": ["osm", "osm"],
        })
        result = rank_cafes(df, "coffee_shop")
        for col in df.columns:
            assert col in result.columns
        assert len(result) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])