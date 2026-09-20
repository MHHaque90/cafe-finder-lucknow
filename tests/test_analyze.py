"""Unit tests for cafe_finder analyze module."""

import pytest
import pandas as pd

from cafe_finder import analyze


def make_test_df(**kwargs) -> pd.DataFrame:
    """Create a test DataFrame with default cafe-like data."""
    default_data = {
        "osm_id": ["node1", "node2", "node3", "node4"],
        "name": ["Cafe A", "Cafe B", "Cafe A", None],
        "latitude": [26.8, 26.9, 26.8, 27.0],
        "longitude": [80.9, 80.8, 80.9, 81.0],
        "street": ["Street 1", "Street 2", None, "Street 4"],
        "housenumber": ["1", "2", None, "4"],
        "city": ["Lucknow", "Lucknow", None, "Lucknow"],
        "postcode": ["226001", "226002", None, "226004"],
        "cuisine": ["coffee_shop", "tea;coffee_shop", "coffee_shop;bakery", None],
        "opening_hours": ["09:00-18:00", None, "10:00-22:00", "08:00-20:00"],
        "website": ["http://cafea.com", None, "http://cafec.com", None],
        "phone": ["+911234567890", None, None, "+911234567893"],
        "source": ["osm", "osm", "osm", "osm"],
    }
    default_data.update(kwargs)
    return pd.DataFrame(default_data)


class TestLoadCSV:
    """Tests for CSV loading."""

    def test_load_csv_success(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        df = make_test_df()
        df.to_csv(csv_file, index=False)

        loaded = analyze.load_csv(csv_file)
        assert len(loaded) == 4
        assert list(loaded.columns) == list(df.columns)

    def test_load_csv_not_found(self, tmp_path):
        missing_file = tmp_path / "missing.csv"
        with pytest.raises(FileNotFoundError):
            analyze.load_csv(missing_file)

    def test_load_csv_empty(self, tmp_path):
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("")
        with pytest.raises(pd.errors.EmptyDataError):
            analyze.load_csv(empty_file)


class TestDataCompleteness:
    """Tests for data completeness calculations."""

    def test_completeness_all_present(self):
        df = make_test_df(name=["A", "B", "C", "D"])
        report = analyze.data_completeness(df)
        assert "name" in report
        assert "4/4 present" in report

    def test_completeness_missing_values(self):
        df = make_test_df(name=["A", "B", None, None])
        report = analyze.data_completeness(df)
        assert "2/4 present" in report
        assert "50.0% missing" in report

    def test_completeness_missing_column(self):
        df = make_test_df()
        df = df.drop(columns=["cuisine"])
        report = analyze.data_completeness(df)
        assert "CUISINE" in report or "cuisine" in report


class TestCafeNamesAnalysis:
    """Tests for cafe names analysis."""

    def test_names_with_duplicates(self):
        df = make_test_df(name=["Cafe A", "Cafe B", "Cafe A", "Cafe C"])
        report = analyze.cafe_names_analysis(df)
        assert "Records with names: 4/4" in report
        assert "Duplicate names found" in report
        assert "Cafe A: 2" in report

    def test_names_no_duplicates(self):
        df = make_test_df(name=["Cafe A", "Cafe B", "Cafe C", "Cafe D"])
        report = analyze.cafe_names_analysis(df)
        assert "No duplicate names found" in report

    def test_names_missing_column(self):
        df = make_test_df()
        df = df.drop(columns=["name"])
        report = analyze.cafe_names_analysis(df)
        assert "not found" in report

    def test_names_partial_missing(self):
        df = make_test_df(name=["A", "B", None, None])
        report = analyze.cafe_names_analysis(df)
        assert "Records with names: 2/4" in report
        assert "Records without names: 2/4" in report


class TestCuisineAnalysis:
    """Tests for cuisine analysis."""

    def test_cuisine_split_counting(self):
        df = make_test_df()
        report = analyze.cuisine_analysis(df)
        assert "coffee_shop" in report
        assert "tea" in report
        assert "bakery" in report

    def test_cuisine_missing_column(self):
        df = make_test_df()
        df = df.drop(columns=["cuisine"])
        report = analyze.cuisine_analysis(df)
        assert "not found" in report

    def test_cuisine_empty_values(self):
        df = make_test_df(cuisine=["", ";", None, "coffee_shop"])
        report = analyze.cuisine_analysis(df)
        assert "coffee_shop: 1" in report


class TestWebsiteAnalysis:
    """Tests for website analysis."""

    def test_website_percentage(self):
        df = make_test_df(website=["http://a.com", None, "http://c.com", None])
        report = analyze.website_analysis(df)
        assert "2/4" in report
        assert "50.0%" in report

    def test_website_missing_column(self):
        df = make_test_df()
        df = df.drop(columns=["website"])
        report = analyze.website_analysis(df)
        assert "not found" in report


class TestPhoneAnalysis:
    """Tests for phone analysis."""

    def test_phone_percentage(self):
        df = make_test_df(phone=["+911", None, None, "+912"])
        report = analyze.phone_analysis(df)
        assert "2/4" in report
        assert "50.0%" in report

    def test_phone_missing_column(self):
        df = make_test_df()
        df = df.drop(columns=["phone"])
        report = analyze.phone_analysis(df)
        assert "not found" in report


class TestOpeningHoursAnalysis:
    """Tests for opening hours analysis."""

    def test_hours_percentage(self):
        df = make_test_df(opening_hours=["09-18", None, "10-22", "08-20"])
        report = analyze.opening_hours_analysis(df)
        assert "3/4" in report
        assert "75.0%" in report

    def test_hours_missing_column(self):
        df = make_test_df()
        df = df.drop(columns=["opening_hours"])
        report = analyze.opening_hours_analysis(df)
        assert "not found" in report


class TestGeographicAnalysis:
    """Tests for geographic analysis."""

    def test_geo_summary(self):
        df = make_test_df(
            latitude=[26.8, 26.9, 27.0, 27.1],
            longitude=[80.9, 80.8, 81.0, 81.1]
        )
        report = analyze.geographic_analysis(df)
        assert "Latitude range: 26.800000 to 27.100000" in report
        assert "Longitude range: 80.800000 to 81.100000" in report
        assert "South (min lat): 26.800000" in report
        assert "North (max lat): 27.100000" in report
        assert "West (min lon):" in report
        assert "80.800000" in report
        assert "East (max lon):" in report
        assert "81.100000" in report

    def test_geo_missing_columns(self):
        df = make_test_df()
        df = df.drop(columns=["latitude", "longitude"])
        report = analyze.geographic_analysis(df)
        assert "not found" in report

    def test_geo_invalid_coords(self):
        df = make_test_df(
            latitude=["invalid", 26.9, None, 27.1],
            longitude=[80.9, "invalid", 81.0, 81.1]
        )
        report = analyze.geographic_analysis(df)
        assert "Valid latitude records: 2/4" in report
        assert "Valid longitude records: 3/4" in report


class TestAddressCompleteness:
    """Tests for address completeness analysis."""

    def test_address_fields(self):
        df = make_test_df(
            street=["S1", "S2", None, "S4"],
            housenumber=["1", "2", None, "4"],
            city=["Lucknow", "Lucknow", None, "Lucknow"],
            postcode=["226001", "226002", None, "226004"]
        )
        report = analyze.address_completeness(df)
        assert "street" in report
        assert "housenumber" in report
        assert "city" in report
        assert "postcode" in report
        # 3 rows have all 4 address fields present
        assert "Records with all address fields: 3/4" in report

    def test_address_missing_columns(self):
        df = make_test_df()
        df = df.drop(columns=["street", "housenumber", "city", "postcode"])
        report = analyze.address_completeness(df)
        assert "No address columns found" in report


class TestDatasetOverview:
    """Tests for dataset overview."""

    def test_overview_content(self):
        df = make_test_df()
        report = analyze.dataset_overview(df)
        assert "Total cafes: 4" in report
        assert "Total columns:" in report
        assert "Data types:" in report
        assert "Memory usage:" in report


class TestGenerateReport:
    """Tests for full report generation."""

    def test_full_report_generation(self):
        df = make_test_df()
        report = analyze.generate_report(df)
        assert "DATASET OVERVIEW" in report
        assert "DATA COMPLETENESS" in report
        assert "CAFE NAMES ANALYSIS" in report
        assert "CUISINE ANALYSIS" in report
        assert "WEBSITE ANALYSIS" in report
        assert "PHONE ANALYSIS" in report
        assert "OPENING HOURS ANALYSIS" in report
        assert "GEOGRAPHIC SUMMARY" in report
        assert "ADDRESS COMPLETENESS" in report
        assert "END OF REPORT" in report


class TestMainEntryPoint:
    """Tests for CLI entry point (basic)."""

    def test_main_with_valid_csv(self, tmp_path, capsys):
        csv_file = tmp_path / "test.csv"
        df = make_test_df()
        df.to_csv(csv_file, index=False)

        # Simulate CLI call
        import sys
        old_argv = sys.argv
        sys.argv = ["analyze", str(csv_file)]
        try:
            analyze.main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

        captured = capsys.readouterr()
        assert "DATASET OVERVIEW" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])