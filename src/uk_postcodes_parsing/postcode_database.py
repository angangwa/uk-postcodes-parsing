"""
Postcode Database Integration
Provides efficient SQLite-based postcode lookups with rich geographic and administrative data
"""

import sqlite3
import threading
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
import math

from .database_manager import ensure_database

logger = logging.getLogger("uk-postcodes-parsing.postcode_database")


@dataclass
class PostcodeResult:
    """Rich postcode result with user-friendly field names"""

    # Core postcode data
    postcode: str
    incode: str
    outcode: str

    # Geographic coordinates
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    eastings: Optional[int] = None
    northings: Optional[int] = None

    # Administrative boundaries
    country: Optional[str] = None
    region: Optional[str] = None
    county: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    parish: Optional[str] = None
    constituency: Optional[str] = None

    # Healthcare regions
    healthcare_region: Optional[str] = None  # Sub ICB Location (formerly CCG)
    nhs_health_authority: Optional[str] = None
    primary_care_trust: Optional[str] = None

    # Statistical areas
    lower_output_area: Optional[str] = None  # LSOA
    middle_output_area: Optional[str] = None  # MSOA
    statistical_region: Optional[str] = None  # ITL (formerly NUTS)

    # Other services
    police_force: Optional[str] = None
    county_division: Optional[str] = None  # County Electoral Division

    # Quality indicators
    coordinate_quality: Optional[int] = None  # 1-10 scale
    date_introduced: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format with clear structure"""
        return {
            "postcode": self.postcode,
            "incode": self.incode,
            "outcode": self.outcode,
            "coordinates": (
                {
                    "latitude": self.latitude,
                    "longitude": self.longitude,
                    "eastings": self.eastings,
                    "northings": self.northings,
                    "quality": self.coordinate_quality,
                }
                if self.latitude or self.longitude
                else None
            ),
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
        score = 0

        # Base score for being in database
        score += 50

        # Geographic data (high value for users)
        if self.latitude and self.longitude:
            score += 25
            if self.coordinate_quality and self.coordinate_quality <= 3:
                score += 15  # High quality coordinates
            elif self.coordinate_quality:
                score += 10  # Medium quality coordinates

        # Administrative data (useful for categorization)
        if self.country:
            score += 5
        if self.district:
            score += 5

        return min(score, 100.0)

    def distance_to(self, other: "PostcodeResult") -> Optional[float]:
        """Calculate distance to another postcode in km using Haversine formula"""
        if not (
            self.latitude and self.longitude and other.latitude and other.longitude
        ):
            return None

        # Haversine formula
        R = 6371  # Earth's radius in km

        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c


class PostcodeDatabase:
    """Thread-safe SQLite database interface for postcode lookups"""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection"""
        if db_path is None:
            # Use database manager for auto-download
            db_path = ensure_database()

        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Postcode database not found at {self.db_path}")

        # Thread-local storage for connections
        self._local = threading.local()

        # Cache for frequently accessed data
        self._outcode_cache = {}
        self._cache_lock = threading.Lock()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(
                str(self.db_path), check_same_thread=False, timeout=10.0
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _row_to_result(self, row: sqlite3.Row) -> PostcodeResult:
        """Convert SQLite row to PostcodeResult with field mapping"""

        # Helper function to safely get values from sqlite3.Row
        def safe_get(row, key, default=None):
            try:
                return row[key]
            except (KeyError, IndexError):
                return default

        # Map database column names to our clean field names
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

        # Normalize postcode
        postcode = postcode.upper().strip()
        pc_compact = postcode.replace(" ", "")

        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM postcodes WHERE postcode = ? OR pc_compact = ?",
            (postcode, pc_compact),
        )

        row = cursor.fetchone()
        return self._row_to_result(row) if row else None

    def search(self, query: str, limit: int = 10) -> List[PostcodeResult]:
        """Search for postcodes matching query (prefix search)"""
        if not query:
            return []

        query = query.upper().strip()
        query_pattern = f"{query}%"

        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM postcodes WHERE postcode LIKE ? ORDER BY postcode LIMIT ?",
            (query_pattern, limit),
        )

        return [self._row_to_result(row) for row in cursor.fetchall()]

    def find_nearest(
        self, latitude: float, longitude: float, radius_km: float = 10, limit: int = 10
    ) -> List[Tuple[PostcodeResult, float]]:
        """Find nearest postcodes within radius"""

        # Rough bounding box for efficiency (1 degree ≈ 111km)
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * math.cos(math.radians(latitude)))

        conn = self._get_connection()
        # Use a subquery approach to filter by calculated distance
        cursor = conn.execute(
            """
            SELECT *, distance FROM (
                SELECT *,
                       (6371 * acos(cos(radians(?)) * cos(radians(latitude)) * 
                       cos(radians(longitude) - radians(?)) + 
                       sin(radians(?)) * sin(radians(latitude)))) AS distance
                FROM postcodes 
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                  AND latitude BETWEEN ? AND ?
                  AND longitude BETWEEN ? AND ?
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
        for row in cursor.fetchall():
            # Extract distance from the row
            distance = row["distance"]

            # Create a new row without the distance column for processing
            postcode_result = self._row_to_result(row)
            results.append((postcode_result, distance))

        return results

    def get_area_postcodes(
        self, area_type: str, area_value: str, limit: Optional[int] = None
    ) -> List[PostcodeResult]:
        """Get postcodes in a specific administrative area"""
        # Map user-friendly area types to database columns
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

        conn = self._get_connection()
        cursor = conn.execute(query, params)

        return [self._row_to_result(row) for row in cursor.fetchall()]

    def get_outcode_postcodes(self, outcode: str) -> List[PostcodeResult]:
        """Get all postcodes in an outcode area"""
        if not outcode:
            return []

        outcode = outcode.upper().strip()

        # Check cache first
        with self._cache_lock:
            if outcode in self._outcode_cache:
                return self._outcode_cache[outcode]

        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM postcodes WHERE outcode = ? ORDER BY postcode", (outcode,)
        )

        results = [self._row_to_result(row) for row in cursor.fetchall()]

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
            return results[0][0]  # Return just the PostcodeResult, not the distance
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = self._get_connection()

        # Get total count
        total = conn.execute("SELECT COUNT(*) FROM postcodes").fetchone()[0]

        # Get coordinate coverage
        with_coords = conn.execute(
            "SELECT COUNT(*) FROM postcodes WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        ).fetchone()[0]

        # Get country breakdown
        countries = conn.execute(
            "SELECT country, COUNT(*) as count FROM postcodes WHERE country IS NOT NULL GROUP BY country ORDER BY count DESC"
        ).fetchall()

        return {
            "total_postcodes": total,
            "with_coordinates": with_coords,
            "coordinate_coverage_percent": (
                round(with_coords / total * 100, 1) if total > 0 else 0
            ),
            "countries": {row[0]: row[1] for row in countries},
            "database_path": str(self.db_path),
            "database_size_mb": round(self.db_path.stat().st_size / (1024 * 1024), 1),
        }

    def close(self):
        """Close database connections"""
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            del self._local.connection


# Global database instance (lazy-loaded)
_db_instance = None
_db_lock = threading.Lock()


def get_database(db_path: Optional[str] = None) -> PostcodeDatabase:
    """Get global database instance (thread-safe)"""
    global _db_instance

    with _db_lock:
        if _db_instance is None:
            _db_instance = PostcodeDatabase(db_path)

    return _db_instance


# Clean API functions
def lookup_postcode(postcode: str) -> Optional[PostcodeResult]:
    """Look up a postcode with rich data

    Args:
        postcode: UK postcode (e.g. "SW1A 1AA" or "SW1A1AA")

    Returns:
        PostcodeResult with geographic and administrative data, or None if not found or database unavailable
    """
    try:
        return get_database().lookup(postcode)
    except Exception as e:
        logger.error(f"Database lookup failed for '{postcode}': {e}")
        logger.error("Enhanced postcode features unavailable - database not accessible")
        return None


def search_postcodes(query: str, limit: int = 10) -> List[PostcodeResult]:
    """Search postcodes by prefix

    Args:
        query: Postcode prefix (e.g. "SW1A", "SW1")
        limit: Maximum number of results

    Returns:
        List of matching PostcodeResult objects, or empty list if database unavailable
    """
    try:
        return get_database().search(query, limit)
    except Exception as e:
        logger.error(f"Database search failed for '{query}': {e}")
        logger.error("Enhanced search features unavailable - database not accessible")
        return []


def find_nearest(
    latitude: float, longitude: float, radius_km: float = 10, limit: int = 10
) -> List[Tuple[PostcodeResult, float]]:
    """Find nearest postcodes to coordinates

    Args:
        latitude: WGS84 latitude
        longitude: WGS84 longitude
        radius_km: Search radius in kilometers
        limit: Maximum number of results

    Returns:
        List of (PostcodeResult, distance_km) tuples, sorted by distance, or empty list if database unavailable
    """
    try:
        return get_database().find_nearest(latitude, longitude, radius_km, limit)
    except Exception as e:
        logger.error(
            f"Database spatial search failed for ({latitude}, {longitude}): {e}"
        )
        logger.error("Enhanced spatial features unavailable - database not accessible")
        return []


def get_area_postcodes(
    area_type: str, area_value: str, limit: Optional[int] = None
) -> List[PostcodeResult]:
    """Get postcodes in administrative area

    Args:
        area_type: Type of area ('country', 'region', 'district', 'county', 'constituency', 'healthcare_region')
        area_value: Name of the area (e.g. 'Westminster', 'London')
        limit: Maximum number of results

    Returns:
        List of PostcodeResult objects in the area, or empty list if database unavailable
    """
    try:
        return get_database().get_area_postcodes(area_type, area_value, limit)
    except Exception as e:
        logger.error(f"Database area search failed for {area_type}='{area_value}': {e}")
        logger.error(
            "Enhanced area search features unavailable - database not accessible"
        )
        return []


def reverse_geocode(latitude: float, longitude: float) -> Optional[PostcodeResult]:
    """Find postcode closest to coordinates

    Args:
        latitude: WGS84 latitude
        longitude: WGS84 longitude

    Returns:
        Closest PostcodeResult, or None if none found within 1km or database unavailable
    """
    try:
        return get_database().reverse_geocode(latitude, longitude)
    except Exception as e:
        logger.error(
            f"Database reverse geocode failed for ({latitude}, {longitude}): {e}"
        )
        logger.error("Enhanced reverse geocoding unavailable - database not accessible")
        return None


def get_outcode_postcodes(outcode: str) -> List[PostcodeResult]:
    """Get all postcodes in an outcode area

    Args:
        outcode: Postcode outcode (e.g. "SW1A")

    Returns:
        List of all PostcodeResult objects with that outcode, or empty list if database unavailable
    """
    try:
        return get_database().get_outcode_postcodes(outcode)
    except Exception as e:
        logger.error(f"Database outcode search failed for '{outcode}': {e}")
        logger.error("Enhanced outcode search unavailable - database not accessible")
        return []
