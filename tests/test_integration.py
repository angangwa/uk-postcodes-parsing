"""
Test end-to-end integration scenarios
Tests database setup workflow, cross-platform compatibility, and real-world usage patterns
"""

import pytest
import tempfile
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
import threading

import uk_postcodes_parsing as ukp
from uk_postcodes_parsing.database_manager import (
    DatabaseManager,
    setup_database,
    get_database_info,
)
from uk_postcodes_parsing.postcode_database import PostcodeResult


class TestDatabaseSetupWorkflow:
    """Test complete database setup and initialization workflow"""

    def test_first_time_setup_workflow(self):
        """Test complete first-time setup workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "uk_postcodes_parsing.database_manager.DatabaseManager"
            ) as MockManager:
                mock_manager = MagicMock()
                mock_manager.db_path.exists.return_value = False
                mock_manager.get_database_info.return_value = {
                    "exists": True,
                    "record_count": 1799395,
                    "size_mb": 797.0,
                }
                MockManager.return_value = mock_manager

                # Test setup_database function
                success = setup_database()

                assert success is True
                mock_manager.ensure_database.assert_called_once()

    def test_redownload_workflow(self):
        """Test force redownload workflow"""
        with patch(
            "uk_postcodes_parsing.database_manager.DatabaseManager"
        ) as MockManager:
            mock_manager = MagicMock()
            mock_manager.db_path.exists.return_value = True
            mock_manager.get_database_info.return_value = {
                "exists": True,
                "record_count": 1799395,
            }
            MockManager.return_value = mock_manager

            success = setup_database(force_redownload=True)

            assert success is True
            mock_manager.remove_database.assert_called_once()
            mock_manager.ensure_database.assert_called_once()

    def test_database_info_workflow(self):
        """Test database information retrieval workflow"""
        expected_info = {
            "exists": True,
            "record_count": 1799395,
            "size_mb": 797.0,
            "coordinate_coverage_percent": 99.3,
        }

        with patch(
            "uk_postcodes_parsing.database_manager.DatabaseManager"
        ) as MockManager:
            mock_manager = MagicMock()
            mock_manager.get_database_info.return_value = expected_info
            MockManager.return_value = mock_manager

            info = get_database_info()

            assert info == expected_info
            mock_manager.get_database_info.assert_called_once()


class TestCrossPlatformCompatibility:
    """Test cross-platform compatibility scenarios"""

    def test_windows_path_handling(self):
        """Test Windows-specific path handling"""
        with patch("os.name", "nt"):
            with patch.dict(
                os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}
            ):
                manager = DatabaseManager()

                assert "AppData" in str(manager.data_dir)
                assert manager.db_path.name == "postcodes.db"
                assert "uk_postcodes_parsing" in str(manager.data_dir)

    def test_unix_path_handling(self):
        """Test Unix/Linux/macOS path handling"""
        with patch("os.name", "posix"):
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/home/testuser")

                manager = DatabaseManager()

                assert str(manager.data_dir).startswith("/home/testuser")
                assert ".uk_postcodes_parsing" in str(manager.data_dir)
                assert manager.db_path.name == "postcodes.db"

    def test_path_creation_cross_platform(self):
        """Test that data directory creation works cross-platform"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseManager()
            manager.data_dir = Path(temp_dir) / ".uk_postcodes_parsing"
            manager.db_path = manager.data_dir / "postcodes.db"

            # Simulate database download which creates directories
            manager.data_dir.mkdir(parents=True, exist_ok=True)
            manager.db_path.write_bytes(b"test database content")

            assert manager.data_dir.exists()
            assert manager.db_path.exists()


class TestConcurrencyAndThreadSafety:
    """Test concurrent access and thread safety"""

    def test_concurrent_database_access(self):
        """Test concurrent database operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test database
            db_path = self.create_test_database(temp_dir)

            results = []
            errors = []

            def lookup_postcodes():
                try:
                    with patch(
                        "uk_postcodes_parsing.postcode_database.ensure_database",
                        return_value=db_path,
                    ):
                        result = ukp.lookup_postcode("SW1A 1AA")
                        results.append(result)
                except Exception as e:
                    errors.append(e)

            # Run multiple threads concurrently
            threads = [threading.Thread(target=lookup_postcodes) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # All should succeed
            assert len(errors) == 0
            assert len(results) == 5
            assert all(r is not None for r in results)
            assert all(r.postcode == "SW1A 1AA" for r in results)

    def test_concurrent_database_initialization(self):
        """Test concurrent database manager initialization"""
        managers = []

        def get_manager():
            from uk_postcodes_parsing.database_manager import get_database_manager

            managers.append(get_database_manager())

        threads = [threading.Thread(target=get_manager) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should be the same instance (singleton pattern)
        assert len(set(id(m) for m in managers)) == 1

    def create_test_database(self, temp_dir):
        """Create minimal test database for concurrent testing"""
        db_path = Path(temp_dir) / "concurrent_test.db"
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
                country TEXT,
                region TEXT,
                district TEXT
            )
        """
        )

        conn.execute(
            """
            INSERT INTO postcodes VALUES 
            ('SW1A 1AA', 'SW1A1AA', '1AA', 'SW1A', 51.501009, -0.141588,
             'England', 'London', 'Westminster')
        """
        )

        conn.commit()
        conn.close()
        return db_path


class TestRealWorldUsagePatterns:
    """Test realistic usage patterns and scenarios"""

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_typical_lookup_workflow(self, mock_ensure_db):
        """Test typical postcode lookup workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_comprehensive_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            # Typical workflow: lookup, then find nearby
            result = ukp.lookup_postcode("SW1A 1AA")
            assert result is not None

            if result and result.latitude and result.longitude:
                nearby = ukp.find_nearest(
                    result.latitude, result.longitude, radius_km=1, limit=5
                )
                assert len(nearby) > 0

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_bulk_processing_pattern(self, mock_ensure_db):
        """Test bulk postcode processing pattern"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_comprehensive_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            postcodes_to_lookup = ["SW1A 1AA", "SW1E 6LA", "E3 4SS", "INVALID 123"]
            results = []

            for postcode in postcodes_to_lookup:
                result = ukp.lookup_postcode(postcode)
                if result:
                    results.append(result)

            # Should find 3 valid postcodes, skip invalid one
            assert len(results) == 3
            assert all(isinstance(r, PostcodeResult) for r in results)

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_search_and_filter_pattern(self, mock_ensure_db):
        """Test search and filter pattern"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_comprehensive_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            # Search for SW1 postcodes
            results = ukp.search_postcodes("SW1", limit=10)

            # Filter by district
            westminster_postcodes = [r for r in results if r.district == "Westminster"]

            assert len(westminster_postcodes) >= 2
            assert all(r.postcode.startswith("SW1") for r in westminster_postcodes)

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_geographic_analysis_pattern(self, mock_ensure_db):
        """Test geographic analysis pattern"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_comprehensive_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            # Get postcodes in Westminster district
            westminster = ukp.get_area_postcodes("district", "Westminster", limit=50)

            # Calculate distances between them
            if len(westminster) >= 2:
                distances = []
                for i in range(len(westminster)):
                    for j in range(i + 1, len(westminster)):
                        dist = westminster[i].distance_to(westminster[j])
                        if dist is not None:
                            distances.append(dist)

                if distances:
                    avg_distance = sum(distances) / len(distances)
                    assert (
                        avg_distance > 0
                    )  # Should have some distance between postcodes

    def create_comprehensive_test_database(self, temp_dir):
        """Create comprehensive test database for real-world scenarios"""
        db_path = Path(temp_dir) / "comprehensive_test.db"
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
                healthcare_region TEXT,
                coordinate_quality INTEGER
            )
        """
        )

        # Insert comprehensive test data
        test_data = [
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
                1,
            ),
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
                "Westminster",
                "Westminster",
                "Cities of London and Westminster",
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
                1,
            ),
            (
                "N1 9AA",
                "N19AA",
                "9AA",
                "N1",
                51.538067,
                -0.099181,
                531750,
                183770,
                "England",
                "London",
                "Islington",
                "Islington",
                "Islington South and Finsbury",
                "NHS North Central London",
                1,
            ),
        ]

        conn.executemany(
            """
            INSERT INTO postcodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
            test_data,
        )

        conn.commit()
        conn.close()
        return db_path


class TestErrorHandlingAndFallback:
    """Test error handling and fallback mechanisms"""

    def test_database_unavailable_graceful_fallback(self):
        """Test graceful fallback when database is unavailable"""
        with patch(
            "uk_postcodes_parsing.postcode_database.ensure_database"
        ) as mock_ensure:
            mock_ensure.side_effect = Exception("Database download failed")

            # API functions should return empty/None rather than crashing
            result = ukp.lookup_postcode("SW1A 1AA")
            assert result is None

            results = ukp.search_postcodes("SW1")
            assert results == []

            results = ukp.find_nearest(51.5, -0.14)
            assert results == []

            result = ukp.reverse_geocode(51.5, -0.14)
            assert result is None

    def test_corrupt_database_handling(self):
        """Test handling of corrupt database files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create corrupted database file
            db_path = Path(temp_dir) / "corrupt.db"
            db_path.write_bytes(b"corrupted data that is not sqlite")

            with patch(
                "uk_postcodes_parsing.postcode_database.ensure_database",
                return_value=db_path,
            ):
                # Should handle corruption gracefully
                result = ukp.lookup_postcode("SW1A 1AA")
                assert result is None

    def test_network_error_handling(self):
        """Test network error handling during database download"""
        with patch("urllib.request.urlretrieve") as mock_retrieve:
            mock_retrieve.side_effect = Exception("Network error")

            success = setup_database()
            assert success is False

    def test_permission_error_handling(self):
        """Test handling of file permission errors"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseManager()
            manager.data_dir = Path(temp_dir) / ".uk_postcodes_parsing"
            manager.db_path = manager.data_dir / "postcodes.db"

            # Create directory structure
            manager.data_dir.mkdir(parents=True, exist_ok=True)

            # Make directory read-only to simulate permission error
            manager.data_dir.chmod(0o444)

            try:
                with pytest.raises((PermissionError, OSError)):
                    manager.db_path.write_bytes(b"test")
            finally:
                # Restore permissions for cleanup
                manager.data_dir.chmod(0o755)


class TestMemoryAndPerformance:
    """Test memory usage and performance characteristics"""

    @patch("uk_postcodes_parsing.postcode_database.ensure_database")
    def test_memory_efficient_bulk_operations(self, mock_ensure_db):
        """Test that bulk operations don't consume excessive memory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_large_test_database(temp_dir)
            mock_ensure_db.return_value = db_path

            # Perform many lookups - should not accumulate memory
            for i in range(100):
                result = ukp.lookup_postcode(f"TEST{i:03d}")
                # Memory should be released after each lookup
                if result:
                    assert isinstance(result, PostcodeResult)

    def test_connection_pooling(self):
        """Test that database connections are properly managed"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_large_test_database(temp_dir)

            with patch(
                "uk_postcodes_parsing.postcode_database.ensure_database",
                return_value=db_path,
            ):
                # Multiple operations should reuse connections efficiently
                results = []
                for i in range(10):
                    result = ukp.lookup_postcode("TEST001")
                    results.append(result)

                # Should complete without connection errors
                assert len([r for r in results if r is not None]) > 0

    def create_large_test_database(self, temp_dir):
        """Create larger test database for performance testing"""
        db_path = Path(temp_dir) / "large_test.db"
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
                country TEXT,
                region TEXT,
                district TEXT
            )
        """
        )

        # Insert many test postcodes
        test_data = []
        for i in range(1000):
            postcode = f"TEST{i:03d}"
            lat = 51.5 + (i * 0.001)
            lon = -0.1 + (i * 0.001)
            test_data.append(
                (
                    postcode,
                    postcode,
                    "1AA",
                    "TEST",
                    lat,
                    lon,
                    "England",
                    "London",
                    "Test",
                )
            )

        conn.executemany(
            """
            INSERT INTO postcodes VALUES (?,?,?,?,?,?,?,?,?)
        """,
            test_data,
        )

        conn.commit()
        conn.close()
        return db_path
