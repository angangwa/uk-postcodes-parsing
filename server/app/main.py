"""
FastAPI Server for UK Postcodes Library
Simple, clean REST API that wraps the uk_postcodes_parsing library
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Literal
from datetime import datetime
import logging
import os

# Import the library
import uk_postcodes_parsing as ukp

# Import configuration
from .config import settings

# Import server-specific models
from .models import (
    PostcodeSearchRequest,
    PostcodeSearchResponse,
    SpatialSearchRequest,
    SpatialSearchResponse,
    ReverseGeocodeRequest,
    BulkPostcodeRequest,
    BulkPostcodeResponse,
    TextParseRequest,
    TextParseResponse,
    AreaPostcodesRequest,
    AreaPostcodesResponse,
    PostcodeValidationRequest,
    PostcodeValidationResponse,
    DistanceCalculationRequest,
    DistanceCalculationResponse,
    ErrorResponse,
    HealthResponse,
    DatabaseInfoResponse,
)

# Import server models for responses
from .models import PostcodeModel, ParsedPostcodeModel

# Setup logging
logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)

# Setup database if custom path provided
if settings.database_path:
    os.environ["UK_POSTCODES_DB_PATH"] = settings.database_path
if settings.auto_download is not None:
    os.environ["UK_POSTCODES_AUTO_DOWNLOAD"] = str(int(settings.auto_download))

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="REST API for UK postcode lookup, parsing, and spatial queries",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.debug,
)

# Add CORS middleware with settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Health and Status Endpoints
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        info = ukp.get_database_info()
        return HealthResponse(
            status="healthy",
            database_loaded=info.get("exists", False),
            database_info=info,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            database_loaded=False,
            timestamp=datetime.utcnow().isoformat(),
        )


@app.get("/database/info", response_model=DatabaseInfoResponse, tags=["Database"])
async def get_database_info():
    """Get database statistics and information"""
    try:
        info = ukp.get_database_info()
        return DatabaseInfoResponse(database_stats=info, status="success")
    except Exception as e:
        logger.error(f"Database info failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Core Postcode Endpoints
@app.get("/postcodes/{postcode}", response_model=PostcodeModel, tags=["Postcodes"])
async def get_postcode(postcode: str):
    """
    Lookup a single postcode

    Returns comprehensive data including coordinates, administrative areas,
    healthcare regions, and statistical information.
    """
    result = ukp.lookup_postcode(postcode)
    if not result:
        raise HTTPException(status_code=404, detail="Postcode not found")
    return PostcodeModel.from_postcode_result(result)


@app.post(
    "/postcodes/search", response_model=PostcodeSearchResponse, tags=["Postcodes"]
)
async def search_postcodes(request: PostcodeSearchRequest):
    """
    Search for postcodes by prefix

    Useful for autocomplete functionality and finding postcodes in a specific area.
    """
    results = ukp.search_postcodes(request.query, request.limit)
    return PostcodeSearchResponse(
        results=[PostcodeModel.from_postcode_result(r) for r in results],
        total_found=len(results),
        query=request.query,
    )


@app.post("/postcodes/bulk", response_model=BulkPostcodeResponse, tags=["Postcodes"])
async def bulk_lookup(request: BulkPostcodeRequest):
    """
    Lookup multiple postcodes in a single request

    Efficient way to lookup up to 100 postcodes at once.
    """
    results = [ukp.lookup_postcode(pc) for pc in request.postcodes]
    pydantic_results = [
        PostcodeModel.from_postcode_result(r) if r else None for r in results
    ]
    found_count = sum(1 for r in results if r)

    return BulkPostcodeResponse(
        results=pydantic_results,
        found_count=found_count,
        total_requested=len(request.postcodes),
        success_rate=found_count / len(request.postcodes) if request.postcodes else 0,
    )


@app.post(
    "/postcodes/validate", response_model=PostcodeValidationResponse, tags=["Postcodes"]
)
async def validate_postcodes(request: PostcodeValidationRequest):
    """
    Validate multiple postcodes for format and database existence

    Checks both format validity and whether the postcode exists in the database.
    """
    validation_results = []

    for postcode in request.postcodes:
        # Check format validity
        parsed = ukp.parse(postcode)
        valid_format = parsed is not None

        # Check database existence
        exists_in_db = False
        if valid_format:
            result = ukp.lookup_postcode(postcode)
            exists_in_db = result is not None

        validation_results.append(
            {
                "postcode": postcode,
                "valid_format": valid_format,
                "exists_in_db": exists_in_db,
                "valid": valid_format and exists_in_db,
            }
        )

    total_valid = sum(1 for r in validation_results if r["valid"])

    return PostcodeValidationResponse(
        results=validation_results,
        total_valid=total_valid,
        total_checked=len(request.postcodes),
        validation_rate=(
            total_valid / len(request.postcodes) if request.postcodes else 0
        ),
    )


# Text Parsing Endpoints
@app.post("/postcodes/parse", response_model=TextParseResponse, tags=["Text Parsing"])
async def parse_text(request: TextParseRequest):
    """
    Parse postcodes from text with OCR error correction

    Extracts postcodes from documents, emails, or any text content.
    Supports automatic correction of common OCR errors.
    """
    postcodes = ukp.parse_from_corpus(
        request.text, request.attempt_fix, request.try_all_fix_options
    )

    return TextParseResponse(
        postcodes=[ParsedPostcodeModel.from_postcode(pc) for pc in postcodes],
        total_found=len(postcodes),
        text_length=len(request.text),
    )


# Spatial Query Endpoints
@app.post("/spatial/nearest", response_model=SpatialSearchResponse, tags=["Spatial"])
async def find_nearest(request: SpatialSearchRequest):
    """
    Find nearest postcodes to given coordinates

    Returns postcodes within the specified radius, sorted by distance.
    """
    results = ukp.find_nearest(
        request.latitude, request.longitude, request.radius_km, request.limit
    )

    formatted_results = [
        {
            "postcode": PostcodeModel.from_postcode_result(postcode),
            "distance_km": distance,
        }
        for postcode, distance in results
    ]

    return SpatialSearchResponse(
        results=formatted_results,
        total_found=len(results),
        search_center={"latitude": request.latitude, "longitude": request.longitude},
        radius_km=request.radius_km,
    )


@app.post("/spatial/reverse-geocode", response_model=PostcodeModel, tags=["Spatial"])
async def reverse_geocode(request: ReverseGeocodeRequest):
    """
    Find the closest postcode to given coordinates

    Reverse geocoding - convert coordinates to the nearest postcode.
    """
    result = ukp.reverse_geocode(request.latitude, request.longitude)
    if not result:
        raise HTTPException(
            status_code=404, detail="No postcode found within search radius"
        )
    return PostcodeModel.from_postcode_result(result)


@app.post(
    "/spatial/distance", response_model=DistanceCalculationResponse, tags=["Spatial"]
)
async def calculate_distance(request: DistanceCalculationRequest):
    """
    Calculate distance between two postcodes

    Uses the Haversine formula to calculate the great circle distance.
    """
    postcode1 = ukp.lookup_postcode(request.postcode1)
    postcode2 = ukp.lookup_postcode(request.postcode2)

    if not postcode1:
        return DistanceCalculationResponse(
            postcode1=request.postcode1,
            postcode2=request.postcode2,
            distance_km=None,
            error=f"Postcode not found: {request.postcode1}",
        )

    if not postcode2:
        return DistanceCalculationResponse(
            postcode1=request.postcode1,
            postcode2=request.postcode2,
            distance_km=None,
            error=f"Postcode not found: {request.postcode2}",
        )

    distance = postcode1.distance_to(postcode2)

    return DistanceCalculationResponse(
        postcode1=request.postcode1, postcode2=request.postcode2, distance_km=distance
    )


# Area-based Query Endpoints
@app.get(
    "/areas/{area_type}/{area_value}",
    response_model=AreaPostcodesResponse,
    tags=["Areas"],
)
async def get_area_postcodes(
    area_type: Literal[
        "country", "region", "district", "county", "constituency", "healthcare_region"
    ],
    area_value: str,
    limit: int = Query(
        100, ge=1, le=10000, description="Maximum number of results (default: 100)"
    ),
):
    """
    Get all postcodes in a specific administrative area

    Supported area types: country, region, district, county, constituency, healthcare_region
    """

    try:
        results = ukp.get_area_postcodes(area_type, area_value, limit)
        return AreaPostcodesResponse(
            results=[PostcodeModel.from_postcode_result(r) for r in results],
            total_found=len(results),
            area_type=area_type,
            area_value=area_value,
        )
    except Exception as e:
        logger.error(f"Area postcodes query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/outcodes/{outcode}", response_model=List[PostcodeModel], tags=["Outcodes"])
async def get_outcode_postcodes(outcode: str):
    """
    Get all postcodes for a specific outcode

    Returns all postcodes that share the same outward code (e.g., all SW1A postcodes).
    """
    results = ukp.get_outcode_postcodes(outcode)
    if not results:
        raise HTTPException(
            status_code=404, detail="No postcodes found for this outcode"
        )

    return [PostcodeModel.from_postcode_result(r) for r in results]


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host=settings.host, port=settings.port
    )  # nosec B104 - required for Docker
