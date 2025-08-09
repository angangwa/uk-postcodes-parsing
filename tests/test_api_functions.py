"""
Test clean API functions with error handling
Tests lookup_postcode, search_postcodes, find_nearest, etc. with database unavailable scenarios
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

import uk_postcodes_parsing as ukp
from uk_postcodes_parsing.postcode_database import PostcodeResult


class TestAPIFunctions:
    """Test clean API functions exposed in uk_postcodes_parsing module"""

    def create_test_database(self, temp_dir):
        """Create minimal test database for API testing"""
        db_path = Path(temp_dir) / "test_api.db"
        conn = sqlite3.connect(str(db_path))

        conn.execute(
            """
            CREATE TABLE postcodes (
                postcode TEXT PRIMARY KEY,
                pc_compact TEXT,
                incode TEXT,
                outcode TEXT,
                latitude REAL,
                longitude REAL,
                eastings INTEGER,
                northings INTEGER,
                country TEXT,
                region TEXT,
                district TEXT,
                admin_district TEXT,
                constituency TEXT,
                ccg TEXT,
                healthcare_region TEXT,
                coordinate_quality INTEGER
            )
        """
        )

        # Insert test data
        test_postcodes = [
            (
                "SW1A 1AA",
                "SW1A1AA",
                "1AA",
                "SW1A",
                51.501009,
                -0.141588,
                529090,
                179645,
                "England",
                "London",
                "Westminster",
                "Westminster",
                "Cities of London and Westminster",
                "NHS North West London",
                "NHS North West London",
                1,
            ),
            (
                "SW1E 6LA",
                "SW1E6LA",
                "6LA",
                "SW1E",
                51.494789,
                -0.134270,
                529650,
                179020,
                "England",
                "London",
                "Westminster",
                "Westminster",
                "Cities of London and Westminster",
                "NHS North West London",
                "NHS North West London",
                1,
            ),
            (
                "E3 4SS",
                "E34SS",
                "4SS",
                "E3",
                51.540300,
                -0.026000,
                537800,
                184000,
                "England",
                "London",
                "Tower Hamlets",
                "Tower Hamlets",
                "Poplar and Limehouse",
                "NHS North East London",
                "NHS North East London",
                1,
            ),
        ]

        conn.executemany(
            """
            INSERT INTO postcodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
            test_postcodes,
        )

        conn.commit()
        conn.close()
        return db_path

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_lookup_postcode_success(self, mock_ensure_db):
        """Test successful postcode lookup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            result = ukp.lookup_postcode("SW1A 1AA")

            assert result is not None
            assert isinstance(result, PostcodeResult)
            assert result.postcode == "SW1A 1AA"
            assert result.latitude == 51.501009
            assert result.longitude == -0.141588
            assert result.district == "Westminster"
            assert result.constituency == "Cities of London and Westminster"

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_lookup_postcode_not_found(self, mock_ensure_db):
        """Test postcode lookup for non-existent postcode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            result = ukp.lookup_postcode("FAKE 123")

            assert result is None

    @patch("uk_postcodes_parsing.postcode_database.get_database")
    def test_lookup_postcode_database_error(self, mock_get_db):
        """Test postcode lookup when database unavailable"""
        mock_get_db.side_effect = Exception("Database connection failed")

        result = ukp.lookup_postcode("SW1A 1AA")

        assert result is None

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_search_postcodes_success(self, mock_ensure_db):
        """Test successful postcode search"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            results = ukp.search_postcodes("SW1", limit=5)

            assert len(results) == 2  # SW1A 1AA and SW1E 6LA
            postcodes = [r.postcode for r in results]
            assert "SW1A 1AA" in postcodes
            assert "SW1E 6LA" in postcodes

            # Results should be PostcodeResult objects
            for result in results:
                assert isinstance(result, PostcodeResult)

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_search_postcodes_empty_query(self, mock_ensure_db):
        """Test search with empty query"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            results = ukp.search_postcodes("")

            assert results == []

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_search_postcodes_limit(self, mock_ensure_db):
        """Test search with limit parameter"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            results = ukp.search_postcodes("SW1", limit=1)

            assert len(results) == 1
            assert isinstance(results[0], PostcodeResult)

    @patch("uk_postcodes_parsing.postcode_database.get_database")
    def test_search_postcodes_database_error(self, mock_get_db):
        """Test search when database unavailable"""
        mock_get_db.side_effect = Exception("Database error")

        results = ukp.search_postcodes("SW1")

        assert results == []

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_find_nearest_success(self, mock_ensure_db):
        """Test successful nearest postcode search"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            # Parliament Square coordinates
            results = ukp.find_nearest(51.5014, -0.1419, radius_km=2, limit=3)

            assert len(results) >= 1

            # Results should be tuples of (PostcodeResult, distance)
            for postcode, distance in results:
                assert isinstance(postcode, PostcodeResult)
                assert isinstance(distance, float)
                assert distance >= 0
                assert distance <= 2.0

            # Should be sorted by distance
            distances = [distance for _, distance in results]
            assert distances == sorted(distances)

            # Closest should be SW1A 1AA
            closest_postcode, _ = results[0]
            assert closest_postcode.postcode == "SW1A 1AA"

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_find_nearest_no_results(self, mock_ensure_db):
        """Test nearest search with no results in radius"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            # Very small radius
            results = ukp.find_nearest(51.5014, -0.1419, radius_km=0.001, limit=10)

            assert results == []

    @patch("uk_postcodes_parsing.postcode_database.get_database")
    def test_find_nearest_database_error(self, mock_get_db):
        """Test find_nearest when database unavailable"""
        mock_get_db.side_effect = Exception("Database error")

        results = ukp.find_nearest(51.5014, -0.1419)

        assert results == []

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_reverse_geocode_success(self, mock_ensure_db):
        """Test successful reverse geocoding"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            # Parliament Square coordinates
            result = ukp.reverse_geocode(51.5014, -0.1419)

            assert result is not None
            assert isinstance(result, PostcodeResult)
            assert result.postcode == "SW1A 1AA"

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_reverse_geocode_no_results(self, mock_ensure_db):
        """Test reverse geocoding with no nearby postcodes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            # Coordinates far from any test postcodes
            result = ukp.reverse_geocode(52.0, 3.0)

            assert result is None

    @patch("uk_postcodes_parsing.postcode_database.get_database")
    def test_reverse_geocode_database_error(self, mock_get_db):
        """Test reverse_geocode when database unavailable"""
        mock_get_db.side_effect = Exception("Database error")

        result = ukp.reverse_geocode(51.5014, -0.1419)

        assert result is None

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_get_area_postcodes_district(self, mock_ensure_db):
        """Test getting postcodes by district"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            results = ukp.get_area_postcodes("district", "Westminster")

            assert len(results) == 2  # SW1A 1AA and SW1E 6LA
            for result in results:
                assert isinstance(result, PostcodeResult)
                assert result.district == "Westminster"

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_get_area_postcodes_constituency(self, mock_ensure_db):
        """Test getting postcodes by constituency"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            results = ukp.get_area_postcodes(
                "constituency", "Cities of London and Westminster"
            )

            assert len(results) == 2
            for result in results:
                assert result.constituency == "Cities of London and Westminster"

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_get_area_postcodes_with_limit(self, mock_ensure_db):
        """Test area postcodes with limit"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            results = ukp.get_area_postcodes("district", "Westminster", limit=1)

            assert len(results) == 1
            assert isinstance(results[0], PostcodeResult)

    @patch("uk_postcodes_parsing.postcode_database.get_database")
    def test_get_area_postcodes_database_error(self, mock_get_db):
        """Test get_area_postcodes when database unavailable"""
        mock_get_db.side_effect = Exception("Database error")

        results = ukp.get_area_postcodes("district", "Westminster")

        assert results == []

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_get_outcode_postcodes_success(self, mock_ensure_db):
        """Test getting postcodes by outcode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            results = ukp.get_outcode_postcodes("SW1A")

            assert len(results) == 1
            assert results[0].postcode == "SW1A 1AA"
            assert isinstance(results[0], PostcodeResult)

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_get_outcode_postcodes_multiple(self, mock_ensure_db):
        """Test getting multiple postcodes by outcode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Add more SW1A postcodes to test database
            db_path = self.create_test_database(temp_dir)

            conn = sqlite3.connect(str(db_path))
            conn.execute(
                """
                INSERT INTO postcodes VALUES 
                ('SW1A 2AA', 'SW1A2AA', '2AA', 'SW1A', 51.503, -0.128, 530240, 179910,
                 'England', 'London', 'Westminster', 'Westminster', 'Cities of London and Westminster',
                 'NHS North West London', 'NHS North West London', 1)
            """
            )
            conn.commit()
            conn.close()

            results = ukp.get_outcode_postcodes("SW1A")

            assert len(results) == 2
            postcodes = [r.postcode for r in results]
            assert "SW1A 1AA" in postcodes
            assert "SW1A 2AA" in postcodes

    @patch("uk_postcodes_parsing.postcode_database.get_database")
    def test_get_outcode_postcodes_database_error(self, mock_get_db):
        """Test get_outcode_postcodes when database unavailable"""
        mock_get_db.side_effect = Exception("Database error")

        results = ukp.get_outcode_postcodes("SW1A")

        assert results == []


class TestAPIImportBehavior:
    """Test API import behavior and graceful degradation"""

    def test_api_functions_exist_when_available(self):
        """Test that API functions are available when imported successfully"""
        # These should be available if database modules import successfully
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

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_api_functions_are_callable(self, mock_ensure_db):
        """Test that API functions are callable"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            # Test that functions can be called without errors
            assert callable(ukp.lookup_postcode)
            assert callable(ukp.search_postcodes)
            assert callable(ukp.find_nearest)
            assert callable(ukp.get_area_postcodes)
            assert callable(ukp.reverse_geocode)
            assert callable(ukp.get_outcode_postcodes)
            assert callable(ukp.setup_database)
            assert callable(ukp.get_database_info)

    def create_test_database(self, temp_dir):
        """Create minimal test database"""
        db_path = Path(temp_dir) / "api_test.db"
        conn = sqlite3.connect(str(db_path))

        conn.execute(
            """
            CREATE TABLE postcodes (
                postcode TEXT PRIMARY KEY,
                pc_compact TEXT,
                incode TEXT,
                outcode TEXT,
                latitude REAL,
                longitude REAL,
                eastings INTEGER,
                northings INTEGER,
                country TEXT,
                region TEXT,
                district TEXT,
                admin_district TEXT,
                constituency TEXT,
                ccg TEXT,
                healthcare_region TEXT
            )
        """
        )

        conn.execute(
            """
            INSERT INTO postcodes VALUES 
            ('SW1A 1AA', 'SW1A1AA', '1AA', 'SW1A', 51.501009, -0.141588, 529090, 179645,
             'England', 'London', 'Westminster', 'Westminster', 'Cities of London and Westminster',
             'NHS North West London', 'NHS North West London')
        """
        )

        conn.commit()
        conn.close()
        return db_path


class TestAPIEdgeCases:
    """Test API functions with edge cases and malformed input"""

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_lookup_empty_postcode(self, mock_ensure_db):
        """Test lookup with empty postcode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "empty.db"
            db_path.touch()
            mock_ensure_db.return_value = db_path

            result = ukp.lookup_postcode("")
            assert result is None

            result = ukp.lookup_postcode(None)
            assert result is None

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_search_special_characters(self, mock_ensure_db):
        """Test search with special characters"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "empty.db"
            db_path.touch()
            mock_ensure_db.return_value = db_path

            # Should handle special characters gracefully
            results = ukp.search_postcodes("SW1%")
            assert results == []

            results = ukp.search_postcodes("SW1'")
            assert results == []

    def test_find_nearest_invalid_coordinates(self):
        """Test find_nearest with invalid coordinates"""
        # Should handle invalid coordinates gracefully
        results = ukp.find_nearest(999, 999)
        assert results == []

        results = ukp.find_nearest(-999, -999)
        assert results == []

    def test_find_nearest_negative_radius(self):
        """Test find_nearest with negative radius"""
        results = ukp.find_nearest(51.5, -0.14, radius_km=-1)
        assert results == []

    def test_get_area_postcodes_invalid_area_type(self):
        """Test get_area_postcodes with invalid area type"""
        results = ukp.get_area_postcodes("invalid_type", "test")
        assert results == []
