"""
Test clean API functions with actual database
Tests lookup_postcode, search_postcodes, find_nearest, etc. using the real database
"""

import pytest
import uk_postcodes_parsing as ukp
from uk_postcodes_parsing.postcode_database import PostcodeResult


class TestAPIFunctions:
    """Test clean API functions exposed in uk_postcodes_parsing module"""

    @classmethod
    def setup_class(cls):
        """Ensure database is available for all tests"""
        # This will download the database if not present
        success = ukp.setup_database()
        if not success:
            pytest.skip("Database setup failed - skipping API tests")

    def test_lookup_postcode_success(self):
        """Test successful postcode lookup"""
        result = ukp.lookup_postcode("SW1A 1AA")

        assert result is not None
        assert isinstance(result, PostcodeResult)
        assert result.postcode == "SW1A 1AA"
        assert result.latitude is not None
        assert result.longitude is not None
        assert result.district == "Westminster"

    def test_lookup_postcode_case_insensitive(self):
        """Test case insensitive postcode lookup"""
        result = ukp.lookup_postcode("sw1a 1aa")

        assert result is not None
        assert result.postcode == "SW1A 1AA"

    def test_lookup_postcode_compact_format(self):
        """Test lookup with compact postcode format"""
        result = ukp.lookup_postcode("SW1A1AA")

        assert result is not None
        assert result.postcode == "SW1A 1AA"

    def test_lookup_postcode_not_found(self):
        """Test postcode lookup for non-existent postcode"""
        result = ukp.lookup_postcode("FAKE 123")

        assert result is None

    def test_lookup_postcode_empty(self):
        """Test lookup with empty postcode"""
        result = ukp.lookup_postcode("")
        assert result is None

        result = ukp.lookup_postcode(None)
        assert result is None

    def test_search_postcodes_success(self):
        """Test successful postcode search"""
        results = ukp.search_postcodes("SW1A", limit=5)

        assert len(results) > 0
        assert len(results) <= 5

        # All results should start with SW1A
        for result in results:
            assert isinstance(result, PostcodeResult)
            assert result.postcode.startswith("SW1A")

    def test_search_postcodes_empty_query(self):
        """Test search with empty query"""
        results = ukp.search_postcodes("")
        assert results == []

    def test_search_postcodes_limit(self):
        """Test search with limit parameter"""
        results_1 = ukp.search_postcodes("SW1", limit=1)
        results_10 = ukp.search_postcodes("SW1", limit=10)

        assert len(results_1) <= 1
        assert len(results_10) <= 10
        
        if len(results_1) > 0 and len(results_10) > 0:
            assert len(results_10) >= len(results_1)

    def test_find_nearest_success(self):
        """Test successful nearest postcode search"""
        # Parliament Square coordinates
        results = ukp.find_nearest(51.5014, -0.1419, radius_km=2, limit=5)

        assert len(results) > 0
        assert len(results) <= 5

        # Results should be tuples of (PostcodeResult, distance)
        for postcode, distance in results:
            assert isinstance(postcode, PostcodeResult)
            assert isinstance(distance, float)
            assert 0 <= distance <= 2.0

        # Should be sorted by distance
        if len(results) > 1:
            distances = [distance for _, distance in results]
            assert distances == sorted(distances)

    def test_find_nearest_small_radius(self):
        """Test nearest search with very small radius"""
        # Very small radius in middle of nowhere
        results = ukp.find_nearest(52.0, 0.0, radius_km=0.001, limit=10)
        
        # Should return empty or very few results
        assert len(results) == 0 or len(results) < 3

    def test_find_nearest_invalid_coordinates(self):
        """Test find_nearest with invalid coordinates"""
        # Invalid latitude (>90)
        results = ukp.find_nearest(999, 0, radius_km=1)
        # Should handle gracefully - implementation dependent
        assert isinstance(results, list)

    def test_reverse_geocode_success(self):
        """Test successful reverse geocoding"""
        # Parliament Square area coordinates
        result = ukp.reverse_geocode(51.5014, -0.1419)

        if result is not None:
            assert isinstance(result, PostcodeResult)
            # Should find a Westminster postcode
            assert result.district == "Westminster"

    def test_reverse_geocode_no_results(self):
        """Test reverse geocoding with no nearby postcodes"""
        # Coordinates far from UK (middle of Atlantic Ocean)
        result = ukp.reverse_geocode(30.0, -30.0)

        assert result is None

    def test_get_area_postcodes_district(self):
        """Test getting postcodes by district"""
        results = ukp.get_area_postcodes("district", "Westminster", limit=10)

        assert len(results) > 0
        assert len(results) <= 10

        for result in results:
            assert isinstance(result, PostcodeResult)
            assert result.district == "Westminster"

    def test_get_area_postcodes_with_limit(self):
        """Test area postcodes with limit"""
        results_1 = ukp.get_area_postcodes("district", "Westminster", limit=1)
        results_5 = ukp.get_area_postcodes("district", "Westminster", limit=5)

        assert len(results_1) <= 1
        assert len(results_5) <= 5

        if len(results_1) > 0 and len(results_5) > 0:
            assert len(results_5) >= len(results_1)

    def test_get_area_postcodes_invalid_type(self):
        """Test get_area_postcodes with invalid area type"""
        results = ukp.get_area_postcodes("invalid_type", "test")
        
        # Should return empty list for invalid area type
        assert results == []

    def test_get_outcode_postcodes_success(self):
        """Test getting postcodes by outcode"""
        results = ukp.get_outcode_postcodes("SW1A")

        assert len(results) > 0

        for result in results:
            assert isinstance(result, PostcodeResult)
            assert result.outcode == "SW1A"

    def test_get_outcode_postcodes_empty(self):
        """Test getting postcodes for non-existent outcode"""
        results = ukp.get_outcode_postcodes("ZZZZ")

        assert results == []


class TestAPIImportBehavior:
    """Test API import behavior"""

    def test_api_functions_exist(self):
        """Test that API functions are available"""
        # Core API functions
        assert hasattr(ukp, "lookup_postcode")
        assert hasattr(ukp, "search_postcodes")
        assert hasattr(ukp, "find_nearest")
        assert hasattr(ukp, "get_area_postcodes")
        assert hasattr(ukp, "reverse_geocode")
        assert hasattr(ukp, "get_outcode_postcodes")
        assert hasattr(ukp, "PostcodeResult")

        # Database management functions
        assert hasattr(ukp, "setup_database")
        assert hasattr(ukp, "get_database_info")

    def test_api_functions_are_callable(self):
        """Test that API functions are callable"""
        assert callable(ukp.lookup_postcode)
        assert callable(ukp.search_postcodes)
        assert callable(ukp.find_nearest)
        assert callable(ukp.get_area_postcodes)
        assert callable(ukp.reverse_geocode)
        assert callable(ukp.get_outcode_postcodes)
        assert callable(ukp.setup_database)
        assert callable(ukp.get_database_info)


class TestDatabaseInfo:
    """Test database information functions"""

    def test_get_database_info(self):
        """Test getting database information"""
        info = ukp.get_database_info()

        assert isinstance(info, dict)
        assert "exists" in info
        assert "path" in info

        if info["exists"]:
            assert "record_count" in info
            assert "size_mb" in info
            assert info["record_count"] > 0
            assert info["size_mb"] > 0