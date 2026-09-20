"""Unit tests for cafe_finder visualize module."""

import pytest
import pandas as pd

from cafe_finder import visualize


def make_test_df(**kwargs) -> pd.DataFrame:
    """Create a test DataFrame with default cafe-like data."""
    default_data = {
        "osm_id": ["node1", "node2", "node3", "node4", "node5"],
        "name": ["Cafe A", "Cafe B", "Cafe A", "Cafe C", None],
        "latitude": [26.8, 26.9, 26.8, 27.0, 27.1],
        "longitude": [80.9, 80.8, 80.9, 81.0, 81.1],
        "street": ["Street 1", "Street 2", None, "Street 4", "Street 5"],
        "housenumber": ["1", "2", None, "4", "5"],
        "city": ["Lucknow", "Lucknow", None, "Lucknow", "Lucknow"],
        "postcode": ["226001", "226002", None, "226004", "226005"],
        "cuisine": ["coffee_shop", "tea;coffee_shop", "coffee_shop;bakery", "pizza", None],
        "opening_hours": ["09:00-18:00", None, "10:00-22:00", "08:00-20:00", None],
        "website": ["http://cafea.com", None, "http://cafec.com", None, None],
        "phone": ["+911234567890", None, None, "+911234567893", None],
        "source": ["osm", "osm", "osm", "osm", "osm"],
    }
    default_data.update(kwargs)
    return pd.DataFrame(default_data)


class TestLoadData:
    """Tests for CSV loading."""

    def test_load_data_success(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        df = make_test_df()
        df.to_csv(csv_file, index=False)

        loaded = visualize.load_data(csv_file)
        assert len(loaded) == 5
        assert list(loaded.columns) == list(df.columns)

    def test_load_data_not_found(self, tmp_path):
        missing_file = tmp_path / "missing.csv"
        with pytest.raises(FileNotFoundError):
            visualize.load_data(missing_file)

    def test_load_data_empty(self, tmp_path):
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("")
        with pytest.raises(pd.errors.EmptyDataError):
            visualize.load_data(empty_file)


class TestPrepareCuisineCounts:
    """Tests for cuisine count preparation."""

    def test_cuisine_split_counting(self):
        df = make_test_df()
        counts = visualize.prepare_cuisine_counts(df)
        assert counts["coffee_shop"] == 3
        assert counts["tea"] == 1
        assert counts["bakery"] == 1
        assert counts["pizza"] == 1
        assert len(counts) == 4

    def test_cuisine_missing_column(self):
        df = make_test_df()
        df = df.drop(columns=["cuisine"])
        counts = visualize.prepare_cuisine_counts(df)
        assert counts.empty

    def test_cuisine_empty_values(self):
        df = make_test_df(cuisine=["", ";", None, "coffee_shop", "tea"])
        counts = visualize.prepare_cuisine_counts(df)
        assert counts["coffee_shop"] == 1
        assert counts["tea"] == 1
        assert len(counts) == 2

    def test_cuisine_whitespace_handling(self):
        df = make_test_df(cuisine=[
            "coffee_shop ; tea",
            " bakery ;pizza ",
            "coffee_shop",
            None,
            "tea ; bakery"
        ])
        counts = visualize.prepare_cuisine_counts(df)
        assert counts["coffee_shop"] == 2
        assert counts["tea"] == 2
        assert counts["bakery"] == 2
        assert counts["pizza"] == 1


class TestCalculateCompleteness:
    """Tests for completeness calculation."""

    def test_completeness_all_present(self):
        df = make_test_df(
            name=["A", "B", "C", "D", "E"],
            street=["S1", "S2", "S3", "S4", "S5"],
            housenumber=["1", "2", "3", "4", "5"],
            city=["Lucknow"] * 5,
            postcode=["1", "2", "3", "4", "5"],
            cuisine=["c1", "c2", "c3", "c4", "c5"],
            opening_hours=["h1", "h2", "h3", "h4", "h5"],
            website=["w1", "w2", "w3", "w4", "w5"],
            phone=["p1", "p2", "p3", "p4", "p5"],
        )
        completeness = visualize.calculate_completeness(df)
        for field in visualize.COMPLETENESS_FIELDS:
            assert completeness[field] == 100.0

    def test_completeness_mixed_missing(self):
        df = make_test_df(
            name=["A", "B", None, None, None],
            street=["S1", "S2", None, None, None],
            housenumber=["1", "2", None, None, None],
            city=["Lucknow", "Lucknow", None, None, None],
            postcode=["1", "2", None, None, None],
            cuisine=["c1", "c2", None, None, None],
            opening_hours=["h1", "h2", None, None, None],
            website=["w1", "w2", None, None, None],
            phone=["p1", "p2", None, None, None],
        )
        completeness = visualize.calculate_completeness(df)
        for field in visualize.COMPLETENESS_FIELDS:
            assert completeness[field] == 40.0  # 2 out of 5

    def test_completeness_empty_strings(self):
        df = make_test_df(
            name=["A", "", None, "B", ""],
            street=["S1", " ", None, "S2", ""],
        )
        completeness = visualize.calculate_completeness(df)
        assert completeness["name"] == 40.0  # 2 out of 5 (A and B)
        assert completeness["street"] == 40.0  # 2 out of 5 (S1 and S2)

    def test_completeness_missing_column(self):
        df = make_test_df()
        df = df.drop(columns=["cuisine", "website"])
        completeness = visualize.calculate_completeness(df)
        assert completeness["cuisine"] == 0.0
        assert completeness["website"] == 0.0

    def test_completeness_empty_dataframe(self):
        df = pd.DataFrame(columns=["name", "street", "cuisine"])
        completeness = visualize.calculate_completeness(df)
        for field in visualize.COMPLETENESS_FIELDS:
            assert completeness[field] == 0.0


class TestPrepareCoordinates:
    """Tests for coordinate preparation."""

    def test_prepare_valid_coordinates(self):
        df = make_test_df(
            latitude=[26.8, 26.9, 27.0, 27.1, 27.2],
            longitude=[80.9, 80.8, 81.0, 81.1, 81.2],
        )
        lats, lons = visualize.prepare_coordinates(df)
        assert len(lats) == 5
        assert len(lons) == 5
        assert lats == [26.8, 26.9, 27.0, 27.1, 27.2]
        assert lons == [80.9, 80.8, 81.0, 81.1, 81.2]

    def test_prepare_invalid_coordinates(self):
        df = make_test_df(
            latitude=["invalid", 26.9, None, 27.1, "bad"],
            longitude=[80.9, "invalid", 81.0, 81.1, 81.2],
        )
        lats, lons = visualize.prepare_coordinates(df)
        assert len(lats) == 1  # Only row 4 has both valid
        assert 27.1 in lats
        assert 81.1 in lons

    def test_prepare_missing_columns(self):
        df = make_test_df()
        df = df.drop(columns=["latitude", "longitude"])
        lats, lons = visualize.prepare_coordinates(df)
        assert lats == []
        assert lons == []


class TestCreateCuisineChart:
    """Tests for cuisine chart creation."""

    def test_create_cuisine_chart_with_data(self, tmp_path):
        counts = pd.Series({"coffee_shop": 10, "tea": 5, "bakery": 3}, name="count")
        output_path = tmp_path / "cuisine.png"
        visualize.create_cuisine_chart(counts, output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_create_cuisine_chart_empty(self, tmp_path):
        counts = pd.Series(dtype=int)
        output_path = tmp_path / "cuisine_empty.png"
        visualize.create_cuisine_chart(counts, output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_create_cuisine_chart_top_n(self, tmp_path):
        # More than MAX_CUISINE_CATEGORIES (15)
        counts = pd.Series({f"cuisine_{i}": i for i in range(20, 0, -1)})
        output_path = tmp_path / "cuisine_top_n.png"
        visualize.create_cuisine_chart(counts, output_path)
        assert output_path.exists()


class TestCreateCompletenessChart:
    """Tests for completeness chart creation."""

    def test_create_completeness_chart(self, tmp_path):
        completeness = {field: float(i * 10) for i, field in enumerate(visualize.COMPLETENESS_FIELDS)}
        output_path = tmp_path / "completeness.png"
        visualize.create_completeness_chart(completeness, output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0


class TestCreateLocationChart:
    """Tests for location chart creation."""

    def test_create_location_chart_with_data(self, tmp_path):
        lats = [26.8, 26.9, 27.0]
        lons = [80.9, 80.8, 81.0]
        output_path = tmp_path / "locations.png"
        visualize.create_location_chart(lats, lons, output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_create_location_chart_empty(self, tmp_path):
        lats = []
        lons = []
        output_path = tmp_path / "locations_empty.png"
        visualize.create_location_chart(lats, lons, output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0


class TestMainEntryPoint:
    """Tests for CLI entry point."""

    def test_main_with_valid_csv(self, tmp_path, capsys):
        csv_file = tmp_path / "test.csv"
        df = make_test_df()
        df.to_csv(csv_file, index=False)

        output_dir = tmp_path / "viz"

        import sys
        old_argv = sys.argv
        sys.argv = ["visualize", str(csv_file), "--output-dir", str(output_dir)]
        try:
            visualize.main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv

        captured = capsys.readouterr()
        assert "cuisine_distribution.png" in captured.out
        assert "data_completeness.png" in captured.out
        assert "cafe_locations.png" in captured.out

        assert (output_dir / "cuisine_distribution.png").exists()
        assert (output_dir / "data_completeness.png").exists()
        assert (output_dir / "cafe_locations.png").exists()

    def test_main_csv_not_found(self, capsys):
        import sys
        old_argv = sys.argv
        sys.argv = ["visualize", "nonexistent.csv"]
        try:
            visualize.main()
        except SystemExit as e:
            assert e.code == 1
        finally:
            sys.argv = old_argv

        captured = capsys.readouterr()
        assert "Error" in captured.err


if __name__ == "__main__":
    pytest.main([__file__, "-v"])