"""
Test end-to-end integration scenarios
Tests database setup workflow, real-world usage patterns using actual database
"""

import pytest
import os
import threading
from pathlib import Path

import uk_postcodes_parsing as ukp
from uk_postcodes_parsing.database_manager import (
    DatabaseManager,
    setup_database,
    get_database_info,
)
from uk_postcodes_parsing.postcode_database import PostcodeResult

# Common test postcodes used across multiple test classes
TEST_POSTCODES = ["SW1A 1AA", "SW1A 2AA", "E1 6AN"]


@pytest.fixture(autouse=True, scope="module")
def ensure_clean_state():
    """Ensure clean state for integration tests by resetting global managers"""
    import uk_postcodes_parsing.database_manager as dm
    import uk_postcodes_parsing.postcode_database as pdb
    
    # Reset any global state from previous tests
    dm._db_manager = None
    pdb._db_instance = None
    
    yield
    
    # Clean up after tests
    dm._db_manager = None
    pdb._db_instance = None


class TestDatabaseSetupWorkflow:
    """Test complete database setup and initialization workflow"""

    def test_database_setup_workflow(self):
        """Test database setup workflow"""
        # Setup database (will download if needed)
        success = setup_database()
        assert success is True

        # Verify database info
        info = get_database_info()
        assert info["exists"] is True
        assert info["record_count"] > 0
        assert info["size_mb"] > 0

    def test_database_info_retrieval(self):
        """Test database information retrieval"""
        info = get_database_info()

        assert isinstance(info, dict)
        assert "exists" in info
        assert "path" in info

        if info["exists"]:
            assert "record_count" in info
            assert "size_mb" in info
            assert Path(info["path"]).exists()


class TestCrossPlatformPaths:
    """Test cross-platform path handling"""

    def test_data_directory_creation(self):
        """Test that data directory is created properly"""
        manager = DatabaseManager()

        # Check that data directory exists or can be created
        assert manager.data_dir is not None
        assert isinstance(manager.data_dir, Path)

        # Directory should be in user's home directory
        home = Path.home()
        assert str(manager.data_dir).startswith(str(home))

    def test_database_path_consistency(self):
        """Test database path is consistent across calls"""
        manager1 = DatabaseManager()
        manager2 = DatabaseManager()

        assert manager1.db_path == manager2.db_path
        assert manager1.data_dir == manager2.data_dir


class TestConcurrencyAndThreadSafety:
    """Test concurrent access and thread safety"""

    @classmethod
    def setup_class(cls):
        """Ensure database is available"""
        success = setup_database()
        if not success:
            pytest.skip("Database setup failed - skipping concurrency tests")

    def test_concurrent_database_lookups(self):
        """Test concurrent database lookups"""
        results = []
        errors = []

        def lookup_postcodes():
            try:
                # Each thread does multiple lookups
                for postcode in TEST_POSTCODES:
                    result = ukp.lookup_postcode(postcode)
                    if result:
                        results.append(result)
            except Exception as e:
                errors.append(e)

        # Run multiple threads concurrently
        threads = [threading.Thread(target=lookup_postcodes) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed without errors
        assert len(errors) == 0
        assert len(results) > 0

    def test_concurrent_spatial_queries(self):
        """Test concurrent spatial queries"""
        all_results = []
        errors = []

        def spatial_search():
            try:
                # Parliament Square coordinates
                results = ukp.find_nearest(51.5014, -0.1419, radius_km=1, limit=3)
                all_results.extend(results)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=spatial_search) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(all_results) > 0


class TestRealWorldUsagePatterns:
    """Test realistic usage patterns and scenarios"""

    @classmethod
    def setup_class(cls):
        """Ensure database is available"""
        success = setup_database()
        if not success:
            pytest.skip("Database setup failed - skipping usage tests")

    def test_typical_lookup_workflow(self):
        """Test typical postcode lookup workflow"""
        # Lookup a postcode
        result = ukp.lookup_postcode("SW1A 1AA")
        assert result is not None

        # Use coordinates to find nearby postcodes
        if result.latitude and result.longitude:
            nearby = ukp.find_nearest(
                result.latitude, result.longitude, radius_km=1, limit=5
            )
            assert len(nearby) > 0

            # First result should be the original postcode or very close
            closest_postcode, distance = nearby[0]
            assert distance < 0.1  # Within 100m

    def test_bulk_processing_pattern(self):
        """Test bulk postcode processing pattern"""
        postcodes_to_lookup = [
            *TEST_POSTCODES,  # Valid postcodes
            "INVALID",   # Invalid
            "",          # Empty
            None,        # None
        ]

        results = []
        for postcode in postcodes_to_lookup:
            result = ukp.lookup_postcode(postcode)
            if result:
                results.append(result)

        # Should find valid postcodes, skip invalid ones
        assert len(results) >= 3
        assert all(isinstance(r, PostcodeResult) for r in results)

    def test_search_and_filter_pattern(self):
        """Test search and filter pattern"""
        # Search for SW1A postcodes (more specific to avoid SW10)
        results = ukp.search_postcodes("SW1A", limit=20)

        # Should find multiple results
        assert len(results) > 0

        # Filter by specific criteria
        westminster_postcodes = [
            r for r in results
            if r.district == "Westminster"
        ]

        # SW1A is definitely in Westminster
        assert len(westminster_postcodes) > 0

    def test_geographic_analysis_pattern(self):
        """Test geographic analysis pattern"""
        # Get postcodes in Westminster district
        westminster = ukp.get_area_postcodes("district", "Westminster", limit=10)

        assert len(westminster) > 0

        # Calculate distances between first postcode and others
        if len(westminster) >= 2:
            first = westminster[0]
            distances = []

            for other in westminster[1:]:
                dist = first.distance_to(other)
                if dist is not None:
                    distances.append(dist)

            # Should have calculated some distances
            assert len(distances) > 0
            # All distances should be positive
            assert all(d >= 0 for d in distances)

    def test_outcode_analysis(self):
        """Test outcode-based analysis"""
        # Get all postcodes in SW1A outcode
        sw1a_postcodes = ukp.get_outcode_postcodes("SW1A")

        assert len(sw1a_postcodes) > 0

        # All should have SW1A outcode
        for postcode in sw1a_postcodes:
            assert postcode.outcode == "SW1A"

        # Should include famous postcodes
        postcodes_list = [p.postcode for p in sw1a_postcodes]
        assert "SW1A 1AA" in postcodes_list  # Buckingham Palace
        assert "SW1A 2AA" in postcodes_list  # 10 Downing Street


class TestDataQuality:
    """Test data quality and consistency"""

    @classmethod  
    def setup_class(cls):
        """Ensure database is available"""
        success = setup_database()
        if not success:
            pytest.skip("Database setup failed - skipping data quality tests")

    def test_postcode_format_consistency(self):
        """Test that postcodes are consistently formatted"""
        # Test various input formats
        test_cases = [
            ("sw1a1aa", "SW1A 1AA"),
            ("SW1A1AA", "SW1A 1AA"),
            ("SW1A 1AA", "SW1A 1AA"),
            (" SW1A 1AA ", "SW1A 1AA"),
        ]

        for input_postcode, expected in test_cases:
            result = ukp.lookup_postcode(input_postcode)
            if result:
                assert result.postcode == expected

    def test_coordinate_validity(self):
        """Test that coordinates are valid"""
        # Sample some postcodes
        results = ukp.search_postcodes("SW1", limit=10)

        for result in results:
            if result.latitude and result.longitude:
                # UK coordinates should be within these bounds
                assert 49.0 <= result.latitude <= 61.0
                assert -8.0 <= result.longitude <= 2.0

    def test_distance_calculation_symmetry(self):
        """Test that distance calculations are symmetric"""
        postcode1 = ukp.lookup_postcode("SW1A 1AA")
        postcode2 = ukp.lookup_postcode("SW1A 2AA")

        if postcode1 and postcode2:
            dist1_to_2 = postcode1.distance_to(postcode2)
            dist2_to_1 = postcode2.distance_to(postcode1)

            if dist1_to_2 is not None and dist2_to_1 is not None:
                # Distances should be equal (within floating point precision)
                assert abs(dist1_to_2 - dist2_to_1) < 0.001


class TestDatabaseStatistics:
    """Test database statistics functionality"""

    @classmethod
    def setup_class(cls):
        """Ensure database is available"""
        success = setup_database()
        if not success:
            pytest.skip("Database setup failed - skipping statistics tests")

    def test_get_statistics(self):
        """Test database statistics retrieval"""
        from uk_postcodes_parsing.postcode_database import get_database

        db = get_database()
        if db:
            stats = db.get_statistics()

            assert isinstance(stats, dict)
            assert stats["total_postcodes"] > 0
            assert stats["with_coordinates"] > 0
            assert 0 <= stats["coordinate_coverage_percent"] <= 100

            # Check countries breakdown
            assert "countries" in stats
            assert isinstance(stats["countries"], dict)
            # UK postcodes include England, Scotland, Wales, Northern Ireland,
            # Channel Islands, and Isle of Man
            if stats["countries"]:
                assert len(stats["countries"]) <= 6