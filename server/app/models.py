"""
Server-specific Pydantic models for FastAPI endpoints
Contains request/response models that are specific to the REST API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any

# Import settings to use configured limits
from .config import settings

# We'll create our own Pydantic models that wrap the library's dataclasses


# Core Response Models (wrapping library dataclasses)
class CoordinatesModel(BaseModel):
    """Geographic coordinates and quality information"""

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    eastings: Optional[int] = None
    northings: Optional[int] = None
    quality: Optional[int] = Field(
        None, description="Coordinate quality indicator (1-9, lower is better)"
    )


class AdministrativeModel(BaseModel):
    """Administrative and political geographic divisions"""

    country: Optional[str] = None
    region: Optional[str] = None
    county: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    parish: Optional[str] = None
    constituency: Optional[str] = None
    county_division: Optional[str] = None


class HealthcareModel(BaseModel):
    """Healthcare administrative regions"""

    healthcare_region: Optional[str] = None
    nhs_health_authority: Optional[str] = None
    primary_care_trust: Optional[str] = None


class StatisticalModel(BaseModel):
    """Statistical geographic areas"""

    lower_output_area: Optional[str] = None
    middle_output_area: Optional[str] = None
    statistical_region: Optional[str] = None


class ServicesModel(BaseModel):
    """Public service areas"""

    police_force: Optional[str] = None


class MetadataModel(BaseModel):
    """Postcode metadata"""

    date_introduced: Optional[str] = None


class PostcodeModel(BaseModel):
    """
    Pydantic model for comprehensive postcode data

    Wraps the library's PostcodeResult for API responses
    """

    postcode: str = Field(..., description="Full postcode (e.g., 'SW1A 1AA')")
    incode: str = Field(..., description="Inward code (e.g., '1AA')")
    outcode: str = Field(..., description="Outward code (e.g., 'SW1A')")
    coordinates: Optional[CoordinatesModel] = None
    administrative: AdministrativeModel
    healthcare: HealthcareModel
    statistical: StatisticalModel
    services: ServicesModel
    metadata: MetadataModel

    @classmethod
    def from_postcode_result(cls, result) -> "PostcodeModel":
        """
        Convert PostcodeResult to Pydantic model

        Args:
            result: PostcodeResult instance from database lookup

        Returns:
            PostcodeModel: Pydantic model with type validation
        """
        data = result.to_dict()

        return cls(
            postcode=data["postcode"],
            incode=data["incode"],
            outcode=data["outcode"],
            coordinates=data.get("coordinates"),
            administrative=data.get("administrative", {}),
            healthcare=data.get("healthcare", {}),
            statistical=data.get("statistical", {}),
            services=data.get("services", {}),
            metadata=data.get("metadata", {}),
        )


class ParsedPostcodeModel(BaseModel):
    """
    Pydantic model for parsed postcode from text

    Wraps the library's Postcode dataclass for API responses
    """

    original: str = Field(..., description="Original text before parsing")
    postcode: str = Field(..., description="Parsed and normalized postcode")
    incode: str = Field(..., description="Inward code component")
    outcode: str = Field(..., description="Outward code component")
    area: str = Field(..., description="Area component (e.g., 'SW')")
    district: str = Field(..., description="District component (e.g., 'SW1')")
    sub_district: Optional[str] = Field(
        None, description="Sub-district component if present"
    )
    sector: str = Field(..., description="Sector component (e.g., 'SW1A 1')")
    unit: str = Field(..., description="Unit component (e.g., 'AA')")
    is_in_ons_postcode_directory: bool = Field(
        ..., description="Whether postcode exists in ONS directory"
    )
    fix_distance: int = Field(
        ...,
        description="Number of characters corrected during parsing (negative if corrected)",
    )

    @classmethod
    def from_postcode(cls, postcode) -> "ParsedPostcodeModel":
        """
        Convert Postcode dataclass to Pydantic model

        Args:
            postcode: Postcode instance from text parsing

        Returns:
            ParsedPostcodeModel: Pydantic model with type validation
        """
        return cls(
            original=postcode.original,
            postcode=postcode.postcode,
            incode=postcode.incode,
            outcode=postcode.outcode,
            area=postcode.area,
            district=postcode.district,
            sub_district=postcode.sub_district,
            sector=postcode.sector,
            unit=postcode.unit,
            is_in_ons_postcode_directory=postcode.is_in_ons_postcode_directory,
            fix_distance=postcode.fix_distance,
        )


class DatabaseStatsModel(BaseModel):
    """Database statistics and information"""

    total_postcodes: int = Field(
        ..., description="Total number of postcodes in database"
    )
    with_coordinates: int = Field(
        ..., description="Number of postcodes with coordinate data"
    )
    coordinate_coverage_percent: float = Field(
        ..., description="Percentage of postcodes with coordinates"
    )
    countries: Dict[str, int] = Field(..., description="Breakdown by country")
    database_path: str = Field(..., description="Path to database file")
    database_size_mb: float = Field(..., description="Database file size in MB")


# Request Models (API-specific)
class PostcodeSearchRequest(BaseModel):
    """Request model for postcode search"""

    query: str = Field(
        ..., min_length=1, max_length=10, description="Search query (e.g., 'SW1A')"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=settings.max_search_results,
        description="Maximum number of results",
    )


class SpatialSearchRequest(BaseModel):
    """Request model for spatial/nearest postcode search"""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    radius_km: float = Field(
        default=10, gt=0, le=50, description="Search radius in kilometers"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=settings.max_search_results,
        description="Maximum number of results",
    )


class ReverseGeocodeRequest(BaseModel):
    """Request model for reverse geocoding"""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")


class BulkPostcodeRequest(BaseModel):
    """Request model for bulk postcode lookup"""

    postcodes: List[str] = Field(
        ...,
        min_length=1,
        max_length=settings.max_bulk_requests,
        description="List of postcodes to lookup",
    )


class TextParseRequest(BaseModel):
    """Request model for parsing postcodes from text"""

    text: str = Field(
        ...,
        min_length=1,
        max_length=settings.max_text_length,
        description="Text to parse postcodes from",
    )
    attempt_fix: bool = Field(default=False, description="Attempt to fix OCR errors")
    try_all_fix_options: bool = Field(
        default=False,
        description="Try all possible corrections (requires attempt_fix=True)",
    )


class AreaPostcodesRequest(BaseModel):
    """Request model for getting postcodes by area"""

    area_type: str = Field(
        ..., description="Type of area (district, county, region, etc.)"
    )
    area_value: str = Field(..., description="Area name/value")
    limit: Optional[int] = Field(
        default=None, ge=1, le=settings.max_area_results, description="Maximum results"
    )


class PostcodeValidationRequest(BaseModel):
    """Request model for postcode validation"""

    postcodes: List[str] = Field(
        ...,
        min_length=1,
        max_length=settings.max_bulk_requests,
        description="List of postcodes to validate",
    )


# Response Models (API-specific)
class PostcodeSearchResponse(BaseModel):
    """Response model for postcode search"""

    results: List[Union[PostcodeModel, dict]]
    total_found: int
    query: str


class SpatialSearchResponse(BaseModel):
    """Response model for spatial search"""

    results: List[dict]  # List of {postcode: PostcodeModel, distance: float}
    total_found: int
    search_center: dict  # {latitude: float, longitude: float}
    radius_km: float


class BulkPostcodeResponse(BaseModel):
    """Response model for bulk lookup"""

    results: List[Optional[Union[PostcodeModel, dict]]]
    found_count: int
    total_requested: int
    success_rate: float


class TextParseResponse(BaseModel):
    """Response model for text parsing"""

    postcodes: List[Union[ParsedPostcodeModel, dict]]
    total_found: int
    text_length: int


class AreaPostcodesResponse(BaseModel):
    """Response model for area-based queries"""

    results: List[Union[PostcodeModel, dict]]
    total_found: int
    area_type: str
    area_value: str


class PostcodeValidationResponse(BaseModel):
    """Response model for validation"""

    results: List[dict]  # List of {postcode: str, valid: bool, exists_in_db: bool}
    total_valid: int
    total_checked: int
    validation_rate: float


class DistanceCalculationRequest(BaseModel):
    """Request model for distance calculation between postcodes"""

    postcode1: str = Field(..., description="First postcode")
    postcode2: str = Field(..., description="Second postcode")


class DistanceCalculationResponse(BaseModel):
    """Response model for distance calculation"""

    postcode1: str
    postcode2: str
    distance_km: Optional[float]
    error: Optional[str] = None


# Error Response Models
class ErrorResponse(BaseModel):
    """Standard error response"""

    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response with detailed field errors"""

    error: str = "Validation Error"
    detail: str
    errors: List[dict]


# Health and Status Models
class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    database_loaded: bool
    database_info: Optional[dict] = None
    timestamp: str


class DatabaseInfoResponse(BaseModel):
    """Database information response"""

    database_stats: Union[DatabaseStatsModel, dict]
    status: str
