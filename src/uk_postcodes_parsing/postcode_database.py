"""
Clean, reliable postcode database implementation following postcodes.io pattern
Uses connection-per-operation for maximum reliability and zero file locking issues
"""

import logging
import math
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Literal

from .database_manager import ensure_database

logger = logging.getLogger(__name__)


@dataclass
class PostcodeResult:
    """Result from postcode database lookup with comprehensive UK postcode data"""

    postcode: str
    incode: str
    outcode: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    eastings: Optional[int] = None
    northings: Optional[int] = None
    country: Optional[str] = None
    region: Optional[str] = None
    county: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    parish: Optional[str] = None
    constituency: Optional[str] = None
    healthcare_region: Optional[str] = None
    nhs_health_authority: Optional[str] = None
    primary_care_trust: Optional[str] = None
    lower_output_area: Optional[str] = None
    middle_output_area: Optional[str] = None
    statistical_region: Optional[str] = None
    police_force: Optional[str] = None
    county_division: Optional[str] = None
    coordinate_quality: Optional[int] = None
    date_introduced: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        coords = None
        if self.latitude and self.longitude:
            coords = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "eastings": self.eastings,
                "northings": self.northings,
                "quality": self.coordinate_quality,
            }

        return {
            "postcode": self.postcode,
            "incode": self.incode,
            "outcode": self.outcode,
            "coordinates": coords,
            "administrative": {
                "country": self.country,
                "region": self.region,
                "county": self.county,
                "district": self.district,
                "ward": self.ward,
                "parish": self.parish,
                "constituency": self.constituency,
                "county_division": self.county_division,
            },
            "healthcare": {
                "healthcare_region": self.healthcare_region,
                "nhs_health_authority": self.nhs_health_authority,
                "primary_care_trust": self.primary_care_trust,
            },
            "statistical": {
                "lower_output_area": self.lower_output_area,
                "middle_output_area": self.middle_output_area,
                "statistical_region": self.statistical_region,
            },
            "services": {
                "police_force": self.police_force,
            },
            "metadata": {
                "date_introduced": self.date_introduced,
            },
        }

    def calculate_confidence(self) -> float:
        """Calculate confidence score (0-100) based on data availability"""
        score = 50  # Base score for being in database

        # Geographic data (high value)
        if self.latitude and self.longitude:
            score += 25
            if self.coordinate_quality and self.coordinate_quality <= 3:
                score += 15  # High quality coordinates
            elif self.coordinate_quality:
                score += 10  # Medium quality coordinates

        # Administrative data
        if self.country:
            score += 5
        if self.district:
            score += 5

        return min(score, 100.0)

    def distance_to(self, other: "PostcodeResult") -> Optional[float]:
        """Calculate distance in kilometers to another postcode using Haversine formula"""
        if not (
            self.latitude and self.longitude and other.latitude and other.longitude
        ):
            return None

        # Haversine formula
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return 6371.0 * c  # Earth's radius in km


class PostcodeDatabase:
    """Simple, reliable SQLite database interface using connection-per-operation pattern"""

    def __init__(
        self, db_path: Optional[str] = None, local_db_path: Optional[str] = None
    ):
        """Initialize database path

        Args:
            db_path: Direct path to database file (deprecated, use local_db_path instead)
            local_db_path: Path to locally-built database file to use
        """
        if db_path is None:
            # Use database manager (supports local_db_path)
            db_path = ensure_database(local_db_path)

        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Postcode database not found at {self.db_path}")

        # Cache for frequently accessed data
        self._outcode_cache = {}
        self._cache_lock = threading.Lock()

    def _execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute query with connection-per-operation pattern"""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close()

    def _execute_query_one(
        self, query: str, params: tuple = ()
    ) -> Optional[sqlite3.Row]:
        """Execute query and return single result"""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(query, params)
            return cursor.fetchone()
        finally:
            conn.close()

    def _row_to_result(self, row: sqlite3.Row) -> PostcodeResult:
        """Convert SQLite row to PostcodeResult"""

        def safe_get(row, key, default=None):
            try:
                return row[key]
            except (KeyError, IndexError):
                return default

        return PostcodeResult(
            postcode=row["postcode"],
            incode=row["incode"],
            outcode=row["outcode"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            eastings=row["eastings"],
            northings=row["northings"],
            country=row["country"],
            region=row["region"],
            county=safe_get(row, "county"),
            district=row["district"],
            ward=safe_get(row, "ward"),
            parish=safe_get(row, "parish"),
            constituency=safe_get(row, "constituency"),
            healthcare_region=safe_get(row, "healthcare_region"),
            nhs_health_authority=safe_get(row, "nhs_health_authority"),
            primary_care_trust=safe_get(row, "primary_care_trust"),
            lower_output_area=safe_get(row, "lower_output_area"),
            middle_output_area=safe_get(row, "middle_output_area"),
            statistical_region=safe_get(row, "statistical_region"),
            police_force=safe_get(row, "police_force"),
            county_division=safe_get(row, "county_division"),
            coordinate_quality=safe_get(row, "coordinate_quality"),
            date_introduced=safe_get(row, "date_introduced"),
        )

    def lookup(self, postcode: str) -> Optional[PostcodeResult]:
        """Look up a single postcode"""
        if not postcode:
            return None

        postcode = postcode.upper().strip()
        pc_compact = postcode.replace(" ", "")

        row = self._execute_query_one(
            "SELECT * FROM postcodes WHERE postcode = ? OR pc_compact = ?",
            (postcode, pc_compact),
        )

        return self._row_to_result(row) if row else None

    def search(self, query: str, limit: int = 10) -> List[PostcodeResult]:
        """Search for postcodes matching query (prefix search)"""
        if not query:
            return []

        query = query.upper().strip()
        query_pattern = f"{query}%"

        rows = self._execute_query(
            "SELECT * FROM postcodes WHERE postcode LIKE ? ORDER BY postcode LIMIT ?",
            (query_pattern, limit),
        )

        return [self._row_to_result(row) for row in rows]

    def find_nearest(
        self, latitude: float, longitude: float, radius_km: float = 10, limit: int = 10
    ) -> List[Tuple[PostcodeResult, float]]:
        """Find nearest postcodes within radius"""
        # Rough bounding box for efficiency
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * math.cos(math.radians(latitude)))

        rows = self._execute_query(
            """
            SELECT *, distance FROM (
                SELECT *,
                       (6371 * acos(cos(radians(?)) * cos(radians(latitude)) * 
                       cos(radians(longitude) - radians(?)) + 
                       sin(radians(?)) * sin(radians(latitude)))) AS distance
                FROM postcodes 
                WHERE latitude BETWEEN ? AND ? 
                AND longitude BETWEEN ? AND ?
                AND latitude IS NOT NULL 
                AND longitude IS NOT NULL
            ) WHERE distance <= ? 
            ORDER BY distance 
            LIMIT ?
            """,
            (
                latitude,
                longitude,
                latitude,
                latitude - lat_delta,
                latitude + lat_delta,
                longitude - lon_delta,
                longitude + lon_delta,
                radius_km,
                limit,
            ),
        )

        results = []
        for row in rows:
            postcode_result = self._row_to_result(row)
            distance = row["distance"]
            results.append((postcode_result, distance))

        return results

    def get_area_postcodes(
        self,
        area_type: Literal[
            "country",
            "region",
            "district",
            "county",
            "constituency",
            "healthcare_region",
        ],
        area_value: str,
        limit: Optional[int] = None,
    ) -> List[PostcodeResult]:
        """Get postcodes in a specific administrative area"""
        area_mappings = {
            "country": "country",
            "region": "region",
            "district": "district",
            "county": "county",
            "constituency": "constituency",
            "healthcare_region": "healthcare_region",
        }

        if area_type not in area_mappings:
            raise ValueError(
                f"Invalid area_type. Must be one of: {list(area_mappings.keys())}"
            )

        column = area_mappings[area_type]
        query = f"SELECT * FROM postcodes WHERE {column} = ? ORDER BY postcode"
        params = [area_value]

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = self._execute_query(query, tuple(params))
        return [self._row_to_result(row) for row in rows]

    def get_outcode_postcodes(self, outcode: str) -> List[PostcodeResult]:
        """Get all postcodes in an outcode area"""
        if not outcode:
            return []

        outcode = outcode.upper().strip()

        # Check cache first
        with self._cache_lock:
            if outcode in self._outcode_cache:
                return self._outcode_cache[outcode]

        rows = self._execute_query(
            "SELECT * FROM postcodes WHERE outcode = ? ORDER BY postcode", (outcode,)
        )

        results = [self._row_to_result(row) for row in rows]

        # Cache result
        with self._cache_lock:
            self._outcode_cache[outcode] = results

        return results

    def reverse_geocode(
        self, latitude: float, longitude: float
    ) -> Optional[PostcodeResult]:
        """Find closest postcode to given coordinates"""
        results = self.find_nearest(latitude, longitude, radius_km=1, limit=1)
        if results:
            return results[0][0]  # Return just the PostcodeResult
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        total_row = self._execute_query_one("SELECT COUNT(*) as total FROM postcodes")
        total = total_row["total"] if total_row else 0

        coords_row = self._execute_query_one(
            "SELECT COUNT(*) as count FROM postcodes WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        )
        with_coords = coords_row["count"] if coords_row else 0

        # Get countries breakdown
        country_rows = self._execute_query(
            "SELECT country, COUNT(*) as count FROM postcodes GROUP BY country"
        )
        countries = {
            row["country"]: row["count"] for row in country_rows if row["country"]
        }

        coverage_percent = (with_coords / total * 100) if total > 0 else 0

        return {
            "total_postcodes": total,
            "with_coordinates": with_coords,
            "coordinate_coverage_percent": round(coverage_percent, 1),
            "countries": countries,
            "database_path": str(self.db_path),
            "database_size_mb": round(self.db_path.stat().st_size / (1024 * 1024), 1),
        }

    def close(self):
        """No-op - connections are closed after each operation"""
        pass


# Global database instance (lazy-loaded)
_db_instance = None
_db_lock = threading.Lock()


def get_database(
    db_path: Optional[str] = None, local_db_path: Optional[str] = None
) -> PostcodeDatabase:
    """Get global database instance (thread-safe)

    Args:
        db_path: Direct path to database file (deprecated)
        local_db_path: Path to locally-built database file to use
    """
    global _db_instance

    with _db_lock:
        if _db_instance is None:
            _db_instance = PostcodeDatabase(db_path, local_db_path)
        elif local_db_path:
            # Check if trying to use different local database
            current_path = str(_db_instance.db_path)
            requested_path = str(Path(local_db_path).resolve())
            if current_path != requested_path:
                logger.warning(f"Database already initialized with {current_path}")
                logger.warning(f"Ignoring new path: {requested_path}")

    return _db_instance


# API functions for convenience
def lookup_postcode(postcode: str) -> Optional[PostcodeResult]:
    """Look up a single postcode using global database instance"""
    try:
        return get_database().lookup(postcode)
    except RuntimeError as e:
        if "UK Postcodes database required" in str(e):
            raise e  # Re-raise helpful database setup error
        return None
    except Exception:
        return None


def search_postcodes(query: str, limit: int = 10) -> List[PostcodeResult]:
    """Search for postcodes using global database instance"""
    try:
        return get_database().search(query, limit)
    except RuntimeError as e:
        if "UK Postcodes database required" in str(e):
            raise e  # Re-raise helpful database setup error
        return []
    except Exception:
        return []


def find_nearest(
    latitude: float, longitude: float, radius_km: float = 10, limit: int = 10
) -> List[Tuple[PostcodeResult, float]]:
    """Find nearest postcodes using global database instance"""
    try:
        return get_database().find_nearest(latitude, longitude, radius_km, limit)
    except RuntimeError as e:
        if "UK Postcodes database required" in str(e):
            raise e  # Re-raise helpful database setup error
        return []
    except Exception:
        return []


def reverse_geocode(latitude: float, longitude: float) -> Optional[PostcodeResult]:
    """Find closest postcode to coordinates using global database instance"""
    try:
        return get_database().reverse_geocode(latitude, longitude)
    except RuntimeError as e:
        if "UK Postcodes database required" in str(e):
            raise e  # Re-raise helpful database setup error
        return None
    except Exception:
        return None


def get_area_postcodes(
    area_type: Literal[
        "country", "region", "district", "county", "constituency", "healthcare_region"
    ],
    area_value: str,
    limit: Optional[int] = None,
) -> List[PostcodeResult]:
    """Get postcodes in administrative area using global database instance"""
    try:
        return get_database().get_area_postcodes(area_type, area_value, limit)
    except RuntimeError as e:
        if "UK Postcodes database required" in str(e):
            raise e  # Re-raise helpful database setup error
        return []
    except Exception:
        return []


def get_outcode_postcodes(outcode: str) -> List[PostcodeResult]:
    """Get all postcodes in outcode using global database instance"""
    try:
        return get_database().get_outcode_postcodes(outcode)
    except RuntimeError as e:
        if "UK Postcodes database required" in str(e):
            raise e  # Re-raise helpful database setup error
        return []
    except Exception:
        return []
