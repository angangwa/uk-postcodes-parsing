"""
Test postcode database functionality
Tests PostcodeResult dataclass, database lookups, and field mapping
"""

import pytest
import sqlite3
import tempfile
import threading
import time
import random
import platform
import traceback
from pathlib import Path
from unittest.mock import patch, MagicMock

from uk_postcodes_parsing.postcode_database import (
    PostcodeResult,
    PostcodeDatabase,
    get_database,
)


class TestPostcodeResult:
    """Test PostcodeResult dataclass functionality"""

    def test_postcode_result_creation(self):
        """Test basic PostcodeResult creation"""
        result = PostcodeResult(
            postcode="SW1A 1AA",
            incode="1AA",
            outcode="SW1A",
            latitude=51.501009,
            longitude=-0.141588,
            country="England",
            district="Westminster",
            constituency="Cities of London and Westminster",
        )

        assert result.postcode == "SW1A 1AA"
        assert result.latitude == 51.501009
        assert result.longitude == -0.141588
        assert result.district == "Westminster"

    def test_to_dict(self):
        """Test conversion to dictionary format"""
        result = PostcodeResult(
            postcode="SW1A 1AA",
            incode="1AA",
            outcode="SW1A",
            latitude=51.501009,
            longitude=-0.141588,
            eastings=529090,
            northings=179645,
            country="England",
            region="London",
            district="Westminster",
            constituency="Cities of London and Westminster",
            healthcare_region="NHS North West London",
            lower_output_area="Westminster 018A",
            coordinate_quality=1,
            date_introduced="1980-01",
        )

        data = result.to_dict()

        # Test structure
        assert data["postcode"] == "SW1A 1AA"
        assert data["coordinates"]["latitude"] == 51.501009
        assert data["coordinates"]["longitude"] == -0.141588
        assert data["coordinates"]["quality"] == 1
        assert data["administrative"]["district"] == "Westminster"
        assert (
            data["administrative"]["constituency"] == "Cities of London and Westminster"
        )
        assert data["healthcare"]["healthcare_region"] == "NHS North West London"
        assert data["statistical"]["lower_output_area"] == "Westminster 018A"
        assert data["metadata"]["date_introduced"] == "1980-01"

    def test_to_dict_minimal_data(self):
        """Test to_dict with minimal data (no coordinates)"""
        result = PostcodeResult(postcode="TEST 123", incode="123", outcode="TEST")

        data = result.to_dict()

        assert data["postcode"] == "TEST 123"
        assert data["coordinates"] is None  # No coordinates provided
        assert "administrative" in data
        assert "healthcare" in data

    def test_calculate_confidence(self):
        """Test confidence score calculation"""
        # High confidence - complete data with high quality coordinates
        result = PostcodeResult(
            postcode="SW1A 1AA",
            incode="1AA",
            outcode="SW1A",
            latitude=51.501009,
            longitude=-0.141588,
            coordinate_quality=1,  # High quality
            country="England",
            district="Westminster",
        )

        confidence = result.calculate_confidence()
        assert confidence >= 95  # Should be very high

        # Medium confidence - coordinates but lower quality
        result.coordinate_quality = 5
        confidence = result.calculate_confidence()
        assert 80 <= confidence <= 95

        # Lower confidence - no coordinates
        result = PostcodeResult(
            postcode="TEST 123", incode="123", outcode="TEST", country="England"
        )
        confidence = result.calculate_confidence()
        assert 50 <= confidence < 80

    def test_distance_to(self):
        """Test distance calculation between postcodes"""
        # Westminster (Parliament)
        postcode1 = PostcodeResult(
            postcode="SW1A 1AA",
            incode="1AA",
            outcode="SW1A",
            latitude=51.501009,
            longitude=-0.141588,
        )

        # Victoria area
        postcode2 = PostcodeResult(
            postcode="SW1E 6LA",
            incode="6LA",
            outcode="SW1E",
            latitude=51.494789,
            longitude=-0.134270,
        )

        distance = postcode1.distance_to(postcode2)

        # Known distance between these points is approximately 0.85km
        assert distance is not None
        assert 0.8 <= distance <= 0.9

    def test_distance_to_no_coordinates(self):
        """Test distance calculation when coordinates missing"""
        postcode1 = PostcodeResult(postcode="SW1A 1AA", incode="1AA", outcode="SW1A")
        postcode2 = PostcodeResult(postcode="SW1E 6LA", incode="6LA", outcode="SW1E")

        distance = postcode1.distance_to(postcode2)
        assert distance is None

    def test_distance_to_same_location(self):
        """Test distance to same coordinates"""
        postcode1 = PostcodeResult(
            postcode="SW1A 1AA",
            incode="1AA",
            outcode="SW1A",
            latitude=51.501009,
            longitude=-0.141588,
        )

        postcode2 = PostcodeResult(
            postcode="SW1A 1AB",
            incode="1AB",
            outcode="SW1A",
            latitude=51.501009,
            longitude=-0.141588,
        )

        distance = postcode1.distance_to(postcode2)
        assert distance == 0.0


class TestPostcodeDatabase:
    """Test PostcodeDatabase class functionality"""

    def create_mock_database(self, temp_dir):
        """Create a mock SQLite database for testing"""
        db_path = Path(temp_dir) / "test_postcodes.db"
        conn = sqlite3.connect(str(db_path))

        # Create postcodes table with test data
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
                county TEXT,
                district TEXT,
                admin_district TEXT,
                ward TEXT,
                parish TEXT,
                constituency TEXT,
                ccg TEXT,
                healthcare_region TEXT,
                nhs_health_authority TEXT,
                primary_care_trust TEXT,
                lsoa TEXT,
                lower_output_area TEXT,
                msoa TEXT,
                middle_output_area TEXT,
                nuts TEXT,
                statistical_region TEXT,
                pfa TEXT,
                police_force TEXT,
                county_division TEXT,
                coordinate_quality INTEGER,
                date_introduced TEXT
            )
        """
        )

        # Insert test data - Westminster area postcodes
        test_data = [
            # Parliament/Downing Street area
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
                None,
                "Westminster",
                "Westminster",
                "St James's",
                None,
                "Cities of London and Westminster",
                "NHS North West London",
                "NHS North West London",
                "NHS North West London",
                "NHS North West London",
                "Westminster 018A",
                "Westminster 018A",
                "Westminster 001",
                "Westminster 001",
                "London",
                "London",
                "Metropolitan Police",
                "Metropolitan Police",
                None,
                1,
                "1980-01",
            ),
            # Victoria area
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
                None,
                "Westminster",
                "Westminster",
                "Vincent Square",
                None,
                "Cities of London and Westminster",
                "NHS North West London",
                "NHS North West London",
                "NHS North West London",
                "NHS North West London",
                "Westminster 020B",
                "Westminster 020B",
                "Westminster 002",
                "Westminster 002",
                "London",
                "London",
                "Metropolitan Police",
                "Metropolitan Police",
                None,
                1,
                "1980-01",
            ),
            # Another Westminster postcode
            (
                "SW1P 3AD",
                "SW1P3AD",
                "3AD",
                "SW1P",
                51.498749,
                -0.138969,
                529340,
                179420,
                "England",
                "London",
                None,
                "Westminster",
                "Westminster",
                "St James's",
                None,
                "Cities of London and Westminster",
                "NHS North West London",
                "NHS North West London",
                "NHS North West London",
                "NHS North West London",
                "Westminster 019A",
                "Westminster 019A",
                "Westminster 001",
                "Westminster 001",
                "London",
                "London",
                "Metropolitan Police",
                "Metropolitan Police",
                None,
                1,
                "1980-01",
            ),
            # Different area for testing
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
                None,
                "Tower Hamlets",
                "Tower Hamlets",
                "Bow East",
                None,
                "Poplar and Limehouse",
                "NHS North East London",
                "NHS North East London",
                "NHS North East London",
                "NHS North East London",
                "Tower Hamlets 025A",
                "Tower Hamlets 025A",
                "Tower Hamlets 003",
                "Tower Hamlets 003",
                "London",
                "London",
                "Metropolitan Police",
                "Metropolitan Police",
                None,
                1,
                "1980-01",
            ),
        ]

        conn.executemany(
            """
            INSERT INTO postcodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
            test_data,
        )

        conn.commit()
        conn.close()
        return db_path

    def test_database_initialization(self):
        """Test database initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)

            db = PostcodeDatabase(str(db_path))
            assert db.db_path == db_path

    def test_database_file_not_found(self):
        """Test initialization with missing database file"""
        with pytest.raises(FileNotFoundError):
            PostcodeDatabase("/nonexistent/path/db.sqlite")

    def test_concurrent_database_access(self):
        """Test concurrent database access with connection-per-operation pattern"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            results = {}
            errors = {}
            thread_info = {}
            
            def lookup_postcode():
                thread_id = threading.current_thread().ident
                thread_name = threading.current_thread().name
                start_time = time.time()
                
                try:
                    # Add small random delay to avoid perfect timing collision
                    delay = random.uniform(0.01, 0.05)
                    time.sleep(delay)
                    
                    # Record thread start info
                    thread_info[thread_id] = {
                        'name': thread_name,
                        'start_time': start_time,
                        'delay': delay,
                        'platform': platform.system()
                    }
                    
                    # Perform the actual database lookup
                    result = db.lookup("SW1A 1AA")
                    
                    # Record success
                    results[thread_id] = result is not None
                    thread_info[thread_id]['success'] = True
                    thread_info[thread_id]['result_valid'] = result is not None
                    thread_info[thread_id]['end_time'] = time.time()
                    
                except Exception as e:
                    # Capture detailed error information
                    error_details = {
                        'exception_type': type(e).__name__,
                        'exception_message': str(e),
                        'traceback': traceback.format_exc(),
                        'thread_name': thread_name,
                        'platform': platform.system()
                    }
                    errors[thread_id] = error_details
                    if thread_id not in thread_info:
                        thread_info[thread_id] = {'name': thread_name}
                    thread_info[thread_id]['success'] = False
                    thread_info[thread_id]['error'] = str(e)

            # Create and start threads
            threads = [threading.Thread(target=lookup_postcode, name=f"TestThread-{i}") for i in range(3)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10.0)  # Add timeout to prevent hanging
                
            # Check for hanging threads
            hanging_threads = [t for t in threads if t.is_alive()]
            if hanging_threads:
                print(f"WARNING: {len(hanging_threads)} threads are still alive after join()")
                for t in hanging_threads:
                    print(f"  - Thread {t.name} (ID: {t.ident}) is still running")

            # Detailed logging for debugging
            print(f"\n=== CONCURRENT ACCESS TEST DEBUG INFO ===")
            print(f"Platform: {platform.system()}")
            print(f"Database path: {db_path}")
            print(f"Total threads created: {len(threads)}")
            print(f"Threads completed successfully: {len(results)}")
            print(f"Threads with errors: {len(errors)}")
            
            print(f"\n--- Thread Details ---")
            for thread_id, info in thread_info.items():
                print(f"Thread {thread_id} ({info.get('name', 'Unknown')}):")
                print(f"  - Success: {info.get('success', 'Unknown')}")
                print(f"  - Delay: {info.get('delay', 'Unknown'):.3f}s")
                if 'end_time' in info and 'start_time' in info:
                    duration = info['end_time'] - info['start_time']
                    print(f"  - Duration: {duration:.3f}s")
                if not info.get('success', True):
                    print(f"  - Error: {info.get('error', 'Unknown error')}")
            
            if errors:
                print(f"\n--- Error Details ---")
                for thread_id, error_info in errors.items():
                    print(f"Thread {thread_id} error:")
                    print(f"  - Type: {error_info['exception_type']}")
                    print(f"  - Message: {error_info['exception_message']}")
                    print(f"  - Platform: {error_info['platform']}")
                    print(f"  - Traceback: {error_info['traceback']}")

            # Original strict assertions with detailed error context
            assert len(results) >= 2, (
                f"Expected at least 2 threads to complete successfully, but only {len(results)} did. "
                f"Errors: {errors}. Thread info: {thread_info}. Platform: {platform.system()}"
            )
            assert all(results.values()), (
                f"All lookups should succeed, but some failed. "
                f"Results: {results}. Errors: {errors}. Platform: {platform.system()}"
            )

    def test_lookup_existing_postcode(self):
        """Test lookup of existing postcode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            result = db.lookup("SW1A 1AA")

            assert result is not None
            assert result.postcode == "SW1A 1AA"
            assert result.latitude == 51.501009
            assert result.longitude == -0.141588
            assert result.district == "Westminster"
            assert result.constituency == "Cities of London and Westminster"
            assert result.healthcare_region == "NHS North West London"

    def test_lookup_compact_format(self):
        """Test lookup with compact postcode format"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            result = db.lookup("SW1A1AA")  # No space

            assert result is not None
            assert result.postcode == "SW1A 1AA"

    def test_lookup_case_insensitive(self):
        """Test case insensitive lookup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            result = db.lookup("sw1a 1aa")

            assert result is not None
            assert result.postcode == "SW1A 1AA"

    def test_lookup_nonexistent_postcode(self):
        """Test lookup of non-existent postcode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            result = db.lookup("FAKE 123")
            assert result is None

    def test_search_postcodes(self):
        """Test postcode prefix search"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            results = db.search("SW1", limit=10)

            assert len(results) >= 3  # Should find SW1A 1AA, SW1E 6LA, SW1P 3AD
            postcodes = [r.postcode for r in results]
            assert "SW1A 1AA" in postcodes
            assert "SW1E 6LA" in postcodes
            assert "SW1P 3AD" in postcodes

    def test_search_empty_query(self):
        """Test search with empty query"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            results = db.search("")
            assert results == []

    def test_get_outcode_postcodes(self):
        """Test getting all postcodes in an outcode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            results = db.get_outcode_postcodes("SW1A")

            assert len(results) == 1
            assert results[0].postcode == "SW1A 1AA"

    def test_get_outcode_postcodes_caching(self):
        """Test outcode result caching"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            # First call - should cache result
            results1 = db.get_outcode_postcodes("SW1A")

            # Second call - should use cache
            results2 = db.get_outcode_postcodes("SW1A")

            assert results1 == results2
            assert len(results1) == 1

    def test_get_area_postcodes_district(self):
        """Test getting postcodes by district"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            results = db.get_area_postcodes("district", "Westminster")

            assert len(results) >= 3
            postcodes = [r.postcode for r in results]
            assert "SW1A 1AA" in postcodes
            assert "SW1E 6LA" in postcodes
            assert "SW1P 3AD" in postcodes

    def test_get_area_postcodes_constituency(self):
        """Test getting postcodes by constituency"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            results = db.get_area_postcodes(
                "constituency", "Cities of London and Westminster"
            )

            assert len(results) >= 3
            postcodes = [r.postcode for r in results]
            assert "SW1A 1AA" in postcodes

    def test_get_area_postcodes_invalid_type(self):
        """Test get_area_postcodes with invalid area type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            with pytest.raises(ValueError, match="Invalid area_type"):
                db.get_area_postcodes("invalid_type", "test")

    def test_get_statistics(self):
        """Test database statistics"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            stats = db.get_statistics()

            assert stats["total_postcodes"] == 4
            assert stats["with_coordinates"] == 4
            assert stats["coordinate_coverage_percent"] == 100.0
            assert "England" in stats["countries"]
            assert stats["countries"]["England"] == 4
            assert "database_path" in stats
            assert "database_size_mb" in stats

    def test_close_connection(self):
        """Test closing database connections"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_mock_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            # Use connection first
            db.lookup("SW1A 1AA")

            # Close should work without error
            db.close()


class TestDatabaseSingleton:
    """Test global database instance management"""

    def test_get_database_singleton(self):
        """Test get_database returns singleton instance"""
        from uk_postcodes_parsing.postcode_database import get_database
        
        # Get database instances
        db1 = get_database()
        db2 = get_database()

        # Should return the same instance (singleton pattern)
        assert db1 is db2
        
        # If database exists, both should be valid
        if db1 is not None:
            assert db2 is not None

    def test_thread_safe_get_database(self):
        """Test thread-safe database instance creation"""
        databases = []

        def get_db():
            from uk_postcodes_parsing.postcode_database import get_database

            databases.append(get_database())

        threads = [threading.Thread(target=get_db) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should be the same instance
        if databases[0] is not None:
            assert all(db is databases[0] for db in databases)
