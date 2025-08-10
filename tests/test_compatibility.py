"""
Test cases for compatibility validation using known test data
Tests validate that our implementation produces consistent results with expected behavior
"""

import json
from pathlib import Path

import pytest

from uk_postcodes_parsing.postcode_database import PostcodeDatabase


class TestCompatibilityValidation:
    """Test compatibility using known test data and expected behavior"""

    @pytest.fixture
    def db(self):
        """Get database instance"""
        return PostcodeDatabase()

    @pytest.fixture
    def bulk_geocoding_data(self):
        """Load bulk geocoding test data"""
        data_file = Path(__file__).parent / "data" / "bulk_geocoding.json"
        with open(data_file, encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def bulk_postcode_data(self):
        """Load bulk postcode test data"""
        data_file = Path(__file__).parent / "data" / "bulk_postcode.json"
        with open(data_file, encoding="utf-8") as f:
            return json.load(f)

    def test_known_postcode_coordinates(self, db, bulk_postcode_data):
        """Test that known postcodes return expected coordinates"""
        for test_case in bulk_postcode_data:
            postcode = test_case["query"]
            expected = test_case["result"]

            result = db.lookup(postcode)

            # Postcode should exist in our database
            assert result is not None, f"Postcode {postcode} not found in database"

            # Verify basic data
            assert result.postcode == expected["postcode"]

            # Verify coordinates match (within reasonable tolerance)
            if expected.get("eastings") and result.eastings:
                assert (
                    abs(result.eastings - expected["eastings"]) <= 1
                ), f"Eastings mismatch for {postcode}: got {result.eastings}, expected {expected['eastings']}"

            if expected.get("northings") and result.northings:
                assert (
                    abs(result.northings - expected["northings"]) <= 1
                ), f"Northings mismatch for {postcode}: got {result.northings}, expected {expected['northings']}"

    def test_reverse_geocoding_validation(self, db, bulk_geocoding_data):
        """Test reverse geocoding with known coordinates"""
        for test_case in bulk_geocoding_data:
            query = test_case["query"]
            expected_results = test_case["result"]

            lat = float(query["latitude"])
            lon = float(query["longitude"])
            radius = float(query.get("radius", 1000)) / 1000  # Convert m to km
            limit = int(query.get("limit", 10))

            results = db.find_nearest(lat, lon, radius_km=radius, limit=limit)

            # Should find some results
            assert len(results) > 0, f"No results found for coordinates {lat}, {lon}"

            # Check that expected postcodes are in the results
            result_postcodes = {r[0].postcode for r in results}
            expected_postcodes = {r["postcode"] for r in expected_results}

            # At least some expected postcodes should be found
            found_expected = expected_postcodes.intersection(result_postcodes)
            assert (
                len(found_expected) > 0
            ), f"None of expected postcodes {expected_postcodes} found in results {result_postcodes}"

    def test_search_ordering_m1_vs_m11(self, db):
        """Test search ordering: M1 should return M1 1AD before M11 1AA"""
        results = db.search("M1", limit=10)

        assert len(results) > 0, "No results found for M1 search"

        postcodes = [r.postcode for r in results]

        # Look for M1 and M11 postcodes
        m1_postcodes = [pc for pc in postcodes if pc.startswith("M1 ")]
        m11_postcodes = [pc for pc in postcodes if pc.startswith("M11 ")]

        if m1_postcodes and m11_postcodes:
            # M1 postcodes should appear before M11 postcodes
            first_m1_index = min(postcodes.index(pc) for pc in m1_postcodes)
            first_m11_index = min(postcodes.index(pc) for pc in m11_postcodes)

            assert (
                first_m1_index < first_m11_index
            ), f"M1 postcodes should appear before M11 postcodes in search results"

    def test_search_ordering_se1_vs_se1p(self, db):
        """Test search ordering: SE1 should return SE1 2DL before SE1P 5ZZ"""
        results = db.search("SE1", limit=10)

        assert len(results) > 0, "No results found for SE1 search"

        postcodes = [r.postcode for r in results]

        # Look for SE1 and SE1P postcodes
        se1_postcodes = [pc for pc in postcodes if pc.startswith("SE1 ")]
        se1p_postcodes = [pc for pc in postcodes if pc.startswith("SE1P ")]

        if se1_postcodes and se1p_postcodes:
            # SE1 postcodes should appear before SE1P postcodes
            first_se1_index = min(postcodes.index(pc) for pc in se1_postcodes)
            first_se1p_index = min(postcodes.index(pc) for pc in se1p_postcodes)

            assert (
                first_se1_index < first_se1p_index
            ), f"SE1 postcodes should appear before SE1P postcodes in search results"

    def test_case_insensitive_search(self, db):
        """Test that searches are case insensitive"""
        # Test with a known postcode area
        upper_results = db.search("SW1A", limit=5)
        lower_results = db.search("sw1a", limit=5)
        mixed_results = db.search("Sw1A", limit=5)

        # All should return the same results
        upper_postcodes = {r.postcode for r in upper_results}
        lower_postcodes = {r.postcode for r in lower_results}
        mixed_postcodes = {r.postcode for r in mixed_results}

        assert (
            upper_postcodes == lower_postcodes == mixed_postcodes
        ), "Case insensitive search should return identical results"

    def test_space_insensitive_lookup(self, db):
        """Test that lookups handle spaces correctly"""
        # Test with a known postcode
        result_spaced = db.lookup("SW1A 1AA")
        result_compact = db.lookup("SW1A1AA")
        result_extra_spaces = db.lookup("SW1A  1AA")

        # All should find the same postcode (or all None if not in database)
        if result_spaced is not None:
            assert result_compact is not None
            assert result_extra_spaces is not None
            assert (
                result_spaced.postcode
                == result_compact.postcode
                == result_extra_spaces.postcode
            )
        else:
            # If postcode doesn't exist, all should be None
            assert result_compact is None
            assert result_extra_spaces is None

    def test_invalid_postcodes_return_none(self, db):
        """Test that invalid postcodes return None"""
        invalid_postcodes = [
            "ID11QE",  # Non-existent postcode from test suite
            "AA1",  # Invalid outcode format
            "XYZ 123",  # Invalid format
            "",  # Empty string
        ]

        for invalid_pc in invalid_postcodes:
            result = db.lookup(invalid_pc)
            assert result is None, f"Invalid postcode {invalid_pc} should return None"

    def test_unreasonable_search_returns_empty(self, db):
        """Test that unreasonable searches return no results"""
        unreasonable_queries = [
            "A0",  # Implausible postcode
            "XYZ",  # Non-existent area
            "",  # Empty query
        ]

        for query in unreasonable_queries:
            results = db.search(query)
            assert (
                len(results) == 0
            ), f"Unreasonable query '{query}' should return no results"

    def test_distance_calculation_accuracy(self, db, bulk_geocoding_data):
        """Test distance calculations between known postcodes"""
        # Use M46 postcodes from test data which are close to each other
        test_case = next(
            (
                tc
                for tc in bulk_geocoding_data
                if any(r["postcode"].startswith("M46") for r in tc["result"])
            ),
            None,
        )

        if test_case:
            expected_results = test_case["result"]
            m46_postcodes = [
                r for r in expected_results if r["postcode"].startswith("M46")
            ]

            if len(m46_postcodes) >= 2:
                pc1_code = m46_postcodes[0]["postcode"]
                pc2_code = m46_postcodes[1]["postcode"]

                pc1 = db.lookup(pc1_code)
                pc2 = db.lookup(pc2_code)

                if pc1 and pc2:
                    distance = pc1.distance_to(pc2)
                    assert (
                        distance is not None
                    ), "Distance calculation should return a value"

                    # Calculate expected distance from eastings/northings
                    e1, n1 = m46_postcodes[0]["eastings"], m46_postcodes[0]["northings"]
                    e2, n2 = m46_postcodes[1]["eastings"], m46_postcodes[1]["northings"]

                    # Simple Euclidean distance in meters
                    expected_distance_m = ((e2 - e1) ** 2 + (n2 - n1) ** 2) ** 0.5
                    expected_distance_km = expected_distance_m / 1000

                    # Allow reasonable tolerance for coordinate system differences
                    tolerance = max(
                        0.1, expected_distance_km * 0.1
                    )  # 10% or 100m minimum
                    assert (
                        abs(distance - expected_distance_km) <= tolerance
                    ), f"Distance mismatch: calculated {distance}km, expected ~{expected_distance_km}km"

    def test_nearest_postcodes_limit_parameter(self, db):
        """Test that nearest postcode searches respect limit parameter"""
        # Use central London coordinates
        lat, lon = 51.5074, -0.1278

        results_10 = db.find_nearest(lat, lon, radius_km=5, limit=10)
        results_5 = db.find_nearest(lat, lon, radius_km=5, limit=5)
        results_1 = db.find_nearest(lat, lon, radius_km=5, limit=1)

        assert len(results_10) <= 10, "Should respect limit of 10"
        assert len(results_5) <= 5, "Should respect limit of 5"
        assert len(results_1) <= 1, "Should respect limit of 1"

        # Smaller limits should return subsets
        assert len(results_1) <= len(results_5) <= len(results_10)

    def test_nearest_postcodes_radius_parameter(self, db):
        """Test that radius parameter affects results"""
        # Use central London coordinates
        lat, lon = 51.5074, -0.1278

        results_1km = db.find_nearest(lat, lon, radius_km=1, limit=10)
        results_5km = db.find_nearest(lat, lon, radius_km=5, limit=10)

        # Larger radius should generally return more results
        assert len(results_5km) >= len(
            results_1km
        ), "Larger radius should return at least as many results"

        # All results from smaller radius should be within larger radius
        small_postcodes = {r[0].postcode for r in results_1km}
        large_postcodes = {r[0].postcode for r in results_5km}

        assert small_postcodes.issubset(
            large_postcodes
        ), "Results from smaller radius should be subset of larger radius results"

    def test_coordinate_precision_consistency(self, db, bulk_postcode_data):
        """Test that coordinate precision is consistent with expected values"""
        for test_case in bulk_postcode_data:
            postcode = test_case["query"]

            result = db.lookup(postcode)

            if result and result.latitude and result.longitude:
                # Our coordinates should be reasonable for UK
                assert (
                    49.0 <= result.latitude <= 61.0
                ), f"Latitude {result.latitude} for {postcode} outside UK range"
                assert (
                    -8.0 <= result.longitude <= 2.0
                ), f"Longitude {result.longitude} for {postcode} outside UK range"
