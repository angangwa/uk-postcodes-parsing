"""
Enhanced Postcode Database Integration
Provides efficient SQLite-based postcode lookups with rich geographic and administrative data
"""

import sqlite3
import threading
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
import math

@dataclass
class PostcodeResult:
    """Enhanced postcode result with all available data"""
    postcode: str
    pc_compact: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    eastings: Optional[int] = None
    northings: Optional[int] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    admin_district: Optional[str] = None
    admin_district_id: Optional[str] = None
    admin_county: Optional[str] = None
    admin_county_id: Optional[str] = None
    admin_ward: Optional[str] = None
    admin_ward_id: Optional[str] = None
    parish: Optional[str] = None
    parish_id: Optional[str] = None
    constituency: Optional[str] = None
    constituency_id: Optional[str] = None
    region: Optional[str] = None
    region_code: Optional[str] = None
    european_electoral_region: Optional[str] = None
    european_electoral_region_code: Optional[str] = None
    ccg: Optional[str] = None
    ccg_id: Optional[str] = None
    primary_care_trust: Optional[str] = None
    primary_care_trust_code: Optional[str] = None
    nhs_ha: Optional[str] = None
    nhs_ha_code: Optional[str] = None
    lsoa: Optional[str] = None
    lsoa_id: Optional[str] = None
    msoa: Optional[str] = None
    msoa_id: Optional[str] = None
    nuts: Optional[str] = None
    nuts_id: Optional[str] = None
    pfa: Optional[str] = None
    pfa_id: Optional[str] = None
    ced: Optional[str] = None
    ced_id: Optional[str] = None
    quality: Optional[int] = None
    date_introduced: Optional[str] = None
    incode: Optional[str] = None
    outcode: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'postcode': self.postcode,
            'pc_compact': self.pc_compact,
            'coordinates': {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'eastings': self.eastings,
                'northings': self.northings,
            } if self.latitude or self.longitude else None,
            'administrative': {
                'country': self.country,
                'admin_district': self.admin_district,
                'admin_county': self.admin_county,
                'admin_ward': self.admin_ward,
                'parish': self.parish,
                'constituency': self.constituency,
                'region': self.region,
                'european_electoral_region': self.european_electoral_region,
            },
            'healthcare': {
                'ccg': self.ccg,
                'primary_care_trust': self.primary_care_trust,
                'nhs_ha': self.nhs_ha,
            },
            'statistical': {
                'lsoa': self.lsoa,
                'msoa': self.msoa,
                'nuts': self.nuts,
                'pfa': self.pfa,
                'ced': self.ced,
            },
            'codes': {
                'country_code': self.country_code,
                'admin_district_id': self.admin_district_id,
                'admin_county_id': self.admin_county_id,
                'admin_ward_id': self.admin_ward_id,
                'parish_id': self.parish_id,
                'constituency_id': self.constituency_id,
                'region_code': self.region_code,
                'european_electoral_region_code': self.european_electoral_region_code,
                'ccg_id': self.ccg_id,
                'primary_care_trust_code': self.primary_care_trust_code,
                'nhs_ha_code': self.nhs_ha_code,
                'lsoa_id': self.lsoa_id,
                'msoa_id': self.msoa_id,
                'nuts_id': self.nuts_id,
                'pfa_id': self.pfa_id,
                'ced_id': self.ced_id,
            },
            'quality': self.quality,
            'date_introduced': self.date_introduced,
            'incode': self.incode,
            'outcode': self.outcode,
        }

    def calculate_confidence(self) -> float:
        """Calculate confidence score (0-100) based on data availability"""
        score = 0
        
        # Base score for being in database
        score += 40
        
        # Geographic data
        if self.latitude and self.longitude:
            score += 20
        elif self.eastings and self.northings:
            score += 15
        
        # Administrative data
        if self.country:
            score += 10
        if self.admin_district:
            score += 10
        
        # Quality indicator
        if self.quality:
            score += min(self.quality * 2, 20)
        
        return min(score, 100.0)

    def distance_to(self, other: 'PostcodeResult') -> Optional[float]:
        """Calculate distance to another postcode in km using Haversine formula"""
        if not (self.latitude and self.longitude and other.latitude and other.longitude):
            return None
        
        # Haversine formula
        R = 6371  # Earth's radius in km
        
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c

class PostcodeDatabase:
    """Thread-safe SQLite database interface for enhanced postcode lookups"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection"""
        if db_path is None:
            # Default to database in same directory as this file
            db_path = Path(__file__).parent / "enhanced_postcodes.db"
        
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
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path), 
                check_same_thread=False,
                timeout=10.0
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _row_to_result(self, row: sqlite3.Row) -> PostcodeResult:
        """Convert SQLite row to PostcodeResult"""
        return PostcodeResult(**dict(row))
    
    def lookup(self, postcode: str) -> Optional[PostcodeResult]:
        """Look up a single postcode"""
        if not postcode:
            return None
        
        # Normalize postcode
        postcode = postcode.upper().strip()
        
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM postcodes WHERE postcode = ? OR pc_compact = ?",
            (postcode, postcode.replace(" ", ""))
        )
        
        row = cursor.fetchone()
        return self._row_to_result(row) if row else None
    
    def lookup_outcode(self, outcode: str) -> List[PostcodeResult]:
        """Look up all postcodes in an outcode area"""
        if not outcode:
            return []
        
        outcode = outcode.upper().strip()
        
        # Check cache first
        with self._cache_lock:
            if outcode in self._outcode_cache:
                return self._outcode_cache[outcode]
        
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM postcodes WHERE outcode = ? ORDER BY postcode",
            (outcode,)
        )
        
        results = [self._row_to_result(row) for row in cursor.fetchall()]
        
        # Cache result
        with self._cache_lock:
            self._outcode_cache[outcode] = results
        
        return results
    
    def search(self, query: str, limit: int = 10) -> List[PostcodeResult]:
        """Search for postcodes matching query (prefix search)"""
        if not query:
            return []
        
        query = query.upper().strip()
        query_pattern = f"{query}%"
        
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM postcodes WHERE postcode LIKE ? OR pc_compact LIKE ? ORDER BY postcode LIMIT ?",
            (query_pattern, query_pattern, limit)
        )
        
        return [self._row_to_result(row) for row in cursor.fetchall()]
    
    def find_nearest(self, latitude: float, longitude: float, 
                    radius_km: float = 10, limit: int = 10) -> List[Tuple[PostcodeResult, float]]:
        """Find nearest postcodes within radius"""
        
        # Rough bounding box for efficiency (1 degree ≈ 111km)
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * math.cos(math.radians(latitude)))
        
        conn = self._get_connection()
        cursor = conn.execute('''
            SELECT *,
                   (6371 * acos(cos(radians(?)) * cos(radians(latitude)) * 
                   cos(radians(longitude) - radians(?)) + 
                   sin(radians(?)) * sin(radians(latitude)))) AS distance
            FROM postcodes 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
              AND latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
            HAVING distance <= ?
            ORDER BY distance
            LIMIT ?
        ''', (latitude, longitude, latitude, 
              latitude - lat_delta, latitude + lat_delta,
              longitude - lon_delta, longitude + lon_delta,
              radius_km, limit))
        
        results = []
        for row in cursor.fetchall():
            # Extract distance from the row
            row_dict = dict(row)
            distance = row_dict.pop('distance')
            
            postcode_result = PostcodeResult(**row_dict)
            results.append((postcode_result, distance))
        
        return results
    
    def get_postcodes_in_area(self, area_type: str, area_value: str, 
                             limit: Optional[int] = None) -> List[PostcodeResult]:
        """Get postcodes in a specific administrative area"""
        valid_area_types = {
            'country': 'country',
            'admin_district': 'admin_district',
            'admin_county': 'admin_county',
            'constituency': 'constituency',
            'region': 'region',
            'ccg': 'ccg'
        }
        
        if area_type not in valid_area_types:
            raise ValueError(f"Invalid area_type. Must be one of: {list(valid_area_types.keys())}")
        
        column = valid_area_types[area_type]
        
        query = f"SELECT * FROM postcodes WHERE {column} = ? ORDER BY postcode"
        params = [area_value]
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        conn = self._get_connection()
        cursor = conn.execute(query, params)
        
        return [self._row_to_result(row) for row in cursor.fetchall()]
    
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
        
        # Get database metadata if available
        metadata = {}
        try:
            meta_cursor = conn.execute("SELECT key, value FROM metadata")
            metadata = {row[0]: row[1] for row in meta_cursor.fetchall()}
        except sqlite3.OperationalError:
            pass  # Metadata table doesn't exist
        
        return {
            'total_postcodes': total,
            'with_coordinates': with_coords,
            'coordinate_coverage_percent': round(with_coords / total * 100, 1) if total > 0 else 0,
            'countries': {row[0]: row[1] for row in countries},
            'database_path': str(self.db_path),
            'database_size_mb': round(self.db_path.stat().st_size / (1024 * 1024), 1),
            'metadata': metadata
        }
    
    def close(self):
        """Close database connections"""
        if hasattr(self._local, 'connection'):
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

# Convenience functions
def lookup_postcode(postcode: str) -> Optional[PostcodeResult]:
    """Look up a postcode using the global database instance"""
    return get_database().lookup(postcode)

def search_postcodes(query: str, limit: int = 10) -> List[PostcodeResult]:
    """Search postcodes using the global database instance"""
    return get_database().search(query, limit)

def find_nearest_postcodes(latitude: float, longitude: float, 
                          radius_km: float = 10, limit: int = 10) -> List[Tuple[PostcodeResult, float]]:
    """Find nearest postcodes using the global database instance"""
    return get_database().find_nearest(latitude, longitude, radius_km, limit)