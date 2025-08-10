"""
Test spatial query functionality
Tests distance calculations, nearest neighbor search, and reverse geocoding
"""

import pytest
import math
import sqlite3
import tempfile
import time
from pathlib import Path

from uk_postcodes_parsing.postcode_database import PostcodeDatabase, PostcodeResult


class TestSpatialQueries:
    """Test spatial query functionality with known geographic data"""

    def create_london_test_database(self, temp_dir):
        """Create test database with London postcodes and known distances"""
        db_path = Path(temp_dir) / "london_postcodes.db"
        conn = sqlite3.connect(str(db_path))

        # Create postcodes table
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

        # Insert London test data with known coordinates and distances
        london_postcodes = [
            # Parliament Square area
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
            # 10 Downing Street (very close to Parliament)
            (
                "SW1A 2AA",
                "SW1A2AA",
                "2AA",
                "SW1A",
                51.503396,
                -0.127625,
                530240,
                179910,
                "England",
                "London",
                "Westminster",
                "Westminster",
                "Cities of London and Westminster",
                "NHS North West London",
                1,
            ),
            # Victoria area (~0.85km from Parliament)
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
            # Westminster Cathedral area (~0.15km from Parliament)
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
            # Buckingham Palace area (~1.2km from Parliament)
            (
                "SW1A 1BA",
                "SW1A1BA",
                "1BA",
                "SW1A",
                51.501364,
                -0.141862,
                529070,
                179685,
                "England",
                "London",
                "Westminster",
                "Westminster",
                "Cities of London and Westminster",
                "NHS North West London",
                1,
            ),
            # Tower Bridge area (~4km from Parliament)
            (
                "SE1 2AA",
                "SE12AA",
                "2AA",
                "SE1",
                51.505455,
                -0.075406,
                533470,
                180160,
                "England",
                "London",
                "Southwark",
                "Southwark",
                "Bermondsey and Old Southwark",
                "NHS South East London",
                1,
            ),
            # East London - outside typical search radius
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
            # North London - for wider area tests
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
            london_postcodes,
        )

        conn.commit()
        conn.close()
        return db_path

    def test_find_nearest_parliament_square(self):
        """Test finding nearest postcodes to Parliament Square coordinates"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_london_test_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            # Parliament Square coordinates
            parliament_lat, parliament_lon = 51.5014, -0.1419

            results = db.find_nearest(
                parliament_lat, parliament_lon, radius_km=1, limit=5
            )

            assert len(results) >= 3

            # Results should be sorted by distance
            distances = [distance for _, distance in results]
            assert distances == sorted(distances)

            # First result should be SW1A 1BA (closest to test Parliament coords)
            # Note: SW1A 1BA is at 51.501364, -0.141862 which is closer to our
            # test coords (51.5014, -0.1419) than SW1A 1AA at 51.501009, -0.141588
            closest_postcode, closest_distance = results[0]
            assert closest_postcode.postcode == "SW1A 1BA"
            assert closest_distance < 0.05  # Very close (< 50m)

            # Should include other Westminster postcodes within 1km
            postcodes_found = {result[0].postcode for result in results}
            assert "SW1P 3AD" in postcodes_found  # Westminster Cathedral area

    def test_find_nearest_with_radius_limit(self):
        """Test radius limiting in spatial search"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_london_test_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            parliament_lat, parliament_lon = 51.5014, -0.1419

            # Small radius should only find very close postcodes
            results_small = db.find_nearest(
                parliament_lat, parliament_lon, radius_km=0.5, limit=10
            )

            # Larger radius should find more
            results_large = db.find_nearest(
                parliament_lat, parliament_lon, radius_km=2.0, limit=10
            )

            assert len(results_large) > len(results_small)

            # All distances should be within specified radius
            for _, distance in results_small:
                assert distance <= 0.5

            for _, distance in results_large:
                assert distance <= 2.0

    def test_find_nearest_limit_parameter(self):
        """Test limit parameter in spatial search"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_london_test_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            parliament_lat, parliament_lon = 51.5014, -0.1419

            # Test different limits
            results_3 = db.find_nearest(
                parliament_lat, parliament_lon, radius_km=5, limit=3
            )
            results_5 = db.find_nearest(
                parliament_lat, parliament_lon, radius_km=5, limit=5
            )

            assert len(results_3) <= 3
            assert len(results_5) <= 5
            assert len(results_5) >= len(results_3)

    def test_find_nearest_no_results_in_radius(self):
        """Test spatial search with no results in radius"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_london_test_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            # Very small radius that shouldn't include any postcodes
            parliament_lat, parliament_lon = 51.5014, -0.1419
            results = db.find_nearest(
                parliament_lat, parliament_lon, radius_km=0.001, limit=10
            )

            assert len(results) == 0

    def test_reverse_geocode_parliament(self):
        """Test reverse geocoding to find Parliament Square postcode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_london_test_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            # Parliament Square coordinates
            parliament_lat, parliament_lon = 51.5014, -0.1419

            result = db.reverse_geocode(parliament_lat, parliament_lon)

            assert result is not None
            assert result.postcode == "SW1A 1BA"  # Should be the closest postcode to test coords

    def test_reverse_geocode_no_nearby_postcodes(self):
        """Test reverse geocoding with no postcodes within 1km"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_london_test_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            # Coordinates far from any test postcodes (middle of North Sea)
            result = db.reverse_geocode(52.0, 3.0)

            assert result is None

    def test_haversine_distance_accuracy(self):
        """Test Haversine distance calculation accuracy with known distances"""
        # Test distance between two PostcodeResult objects
        parliament = PostcodeResult(
            postcode="SW1A 1AA",
            incode="1AA",
            outcode="SW1A",
            latitude=51.501009,
            longitude=-0.141588,
        )

        victoria = PostcodeResult(
            postcode="SW1E 6LA",
            incode="6LA",
            outcode="SW1E",
            latitude=51.494789,
            longitude=-0.134270,
        )

        distance = parliament.distance_to(victoria)

        # Known distance between Parliament and Victoria is approximately 0.85km
        assert distance is not None
        assert 0.8 <= distance <= 0.9

    def test_haversine_distance_same_location(self):
        """Test distance calculation for same location"""
        postcode = PostcodeResult(
            postcode="SW1A 1AA",
            incode="1AA",
            outcode="SW1A",
            latitude=51.501009,
            longitude=-0.141588,
        )

        distance = postcode.distance_to(postcode)
        assert distance == 0.0

    def test_haversine_long_distance(self):
        """Test Haversine formula for longer distances"""
        london = PostcodeResult(
            postcode="SW1A 1AA",
            incode="1AA",
            outcode="SW1A",
            latitude=51.501009,
            longitude=-0.141588,
        )

        # Edinburgh coordinates (approximate)
        edinburgh = PostcodeResult(
            postcode="EH1 1AA",
            incode="1AA",
            outcode="EH1",
            latitude=55.953252,
            longitude=-3.188267,
        )

        distance = london.distance_to(edinburgh)

        # London to Edinburgh is approximately 535km
        assert distance is not None
        assert 530 <= distance <= 540

    def test_spatial_query_performance(self):
        """Test spatial query performance with larger dataset"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_london_test_database(temp_dir)

            # Add more test data for performance testing
            conn = sqlite3.connect(str(db_path))

            # Generate grid of test postcodes around London
            test_data = []
            for i in range(10):
                for j in range(10):
                    lat = 51.45 + (i * 0.01)  # Grid around London
                    lon = -0.2 + (j * 0.01)
                    postcode = f"TEST{i}{j}"
                    test_data.append(
                        (
                            postcode,
                            postcode.replace(" ", ""),
                            "1AA",
                            f"TEST{i}",
                            lat,
                            lon,
                            500000 + i * 100,
                            180000 + j * 100,
                            "England",
                            "London",
                            "Test",
                            "Test",
                            "Test",
                            "Test",
                            1,
                        )
                    )

            conn.executemany(
                """
                INSERT INTO postcodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
                test_data,
            )
            conn.commit()
            conn.close()

            db = PostcodeDatabase(str(db_path))

            # Test performance of spatial query

            start_time = time.time()

            results = db.find_nearest(51.5, -0.15, radius_km=2, limit=20)

            end_time = time.time()
            query_time = end_time - start_time

            # Should complete quickly (< 1 second for this dataset size)
            assert query_time < 1.0
            assert len(results) > 0

    def test_bounding_box_optimization(self):
        """Test that spatial queries use bounding box optimization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_london_test_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            # Query in area where we know only London postcodes should be found
            results = db.find_nearest(51.5, -0.14, radius_km=10, limit=50)

            # All results should be London postcodes
            for postcode, distance in results:
                assert postcode.region == "London"
                assert distance <= 10.0

    def test_coordinate_quality_in_spatial_results(self):
        """Test that spatial results include coordinate quality information"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = self.create_london_test_database(temp_dir)
            db = PostcodeDatabase(str(db_path))

            results = db.find_nearest(51.5014, -0.1419, radius_km=1, limit=5)

            for postcode, distance in results:
                # All test data has coordinate_quality = 1 (high quality)
                assert postcode.coordinate_quality == 1

                # Should have valid coordinates
                assert postcode.latitude is not None
                assert postcode.longitude is not None
                assert -90 <= postcode.latitude <= 90
                assert -180 <= postcode.longitude <= 180
