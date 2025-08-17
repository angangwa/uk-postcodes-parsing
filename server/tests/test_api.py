"""
Comprehensive tests for UK Postcodes FastAPI server
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test health and status endpoints"""

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database_loaded" in data
        assert "timestamp" in data

    def test_database_info(self, client):
        """Test database info endpoint"""
        response = client.get("/database/info")
        assert response.status_code == 200
        data = response.json()
        assert "database_stats" in data
        assert "status" in data


class TestPostcodeEndpoints:
    """Test core postcode endpoints"""

    def test_get_single_postcode_success(self, client, sample_postcodes):
        """Test successful single postcode lookup"""
        postcode = sample_postcodes["valid"][0]
        response = client.get(f"/postcodes/{postcode}")
        assert response.status_code == 200
        data = response.json()
        assert data["postcode"] == postcode
        assert "coordinates" in data
        assert "administrative" in data

    def test_get_single_postcode_not_found(self, client, sample_postcodes):
        """Test postcode not found"""
        postcode = sample_postcodes["invalid"][0]
        response = client.get(f"/postcodes/{postcode}")
        assert response.status_code == 404
        assert "Postcode not found" in response.json()["detail"]

    def test_get_single_postcode_case_insensitive(self, client, sample_postcodes):
        """Test case insensitive postcode lookup"""
        postcode = sample_postcodes["mixed_case"][0]  # "sw1a 1aa"
        response = client.get(f"/postcodes/{postcode}")
        assert response.status_code == 200
        data = response.json()
        assert data["postcode"] == "SW1A 1AA"

    def test_search_postcodes(self, client):
        """Test postcode search"""
        response = client.post("/postcodes/search", json={"query": "SW1A", "limit": 5})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_found" in data
        assert len(data["results"]) <= 5
        assert all(r["postcode"].startswith("SW1A") for r in data["results"])

    def test_bulk_lookup(self, client, sample_postcodes):
        """Test bulk postcode lookup"""
        postcodes = sample_postcodes["valid"][:2] + sample_postcodes["invalid"][:1]
        response = client.post("/postcodes/bulk", json={"postcodes": postcodes})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "found_count" in data
        assert "total_requested" in data
        assert "success_rate" in data
        assert len(data["results"]) == len(postcodes)
        # First two should be successful, third should fail
        assert data["results"][0]["success"] is True
        assert data["results"][0]["postcode"] is not None
        assert data["results"][1]["success"] is True
        assert data["results"][1]["postcode"] is not None
        assert data["results"][2]["success"] is False
        assert data["results"][2]["postcode"] is None
        assert data["results"][2]["error"] == "Postcode not found"

    def test_validate_postcodes(self, client, sample_postcodes):
        """Test postcode validation"""
        postcodes = sample_postcodes["valid"][:1] + sample_postcodes["invalid"][:1]
        response = client.post("/postcodes/validate", json={"postcodes": postcodes})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_valid" in data
        assert "validation_rate" in data
        # First should be valid, second invalid
        assert data["results"][0]["valid"] is True
        assert data["results"][1]["valid"] is False


class TestTextParsingEndpoints:
    """Test text parsing endpoints"""

    def test_parse_text_simple(self, client, sample_text):
        """Test parsing postcodes from simple text"""
        response = client.post(
            "/postcodes/parse",
            json={"text": sample_text["simple"], "attempt_fix": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert "postcodes" in data
        assert "total_found" in data
        assert data["total_found"] == 2

    def test_parse_text_with_ocr_fix(self, client, sample_text):
        """Test parsing with OCR error correction"""
        response = client.post(
            "/postcodes/parse",
            json={"text": sample_text["with_ocr_errors"], "attempt_fix": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_found"] >= 1  # Should find at least E1 6AN

    def test_parse_text_no_postcodes(self, client, sample_text):
        """Test parsing text with no postcodes"""
        response = client.post(
            "/postcodes/parse",
            json={"text": sample_text["no_postcodes"], "attempt_fix": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_found"] == 0
        assert data["postcodes"] == []


class TestSpatialEndpoints:
    """Test spatial query endpoints"""

    def test_find_nearest(self, client, sample_coordinates):
        """Test finding nearest postcodes"""
        coords = sample_coordinates["parliament"]
        response = client.post(
            "/spatial/nearest",
            json={
                "latitude": coords["latitude"],
                "longitude": coords["longitude"],
                "radius_km": 2,
                "limit": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_found" in data
        assert "search_center" in data
        assert len(data["results"]) <= 5
        # Results should have postcode and distance
        if data["results"]:
            assert "postcode" in data["results"][0]
            assert "distance_km" in data["results"][0]

    def test_reverse_geocode(self, client, sample_coordinates):
        """Test reverse geocoding"""
        coords = sample_coordinates["parliament"]
        response = client.post(
            "/spatial/reverse-geocode",
            json={"latitude": coords["latitude"], "longitude": coords["longitude"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "postcode" in data
        assert "coordinates" in data

    def test_reverse_geocode_not_found(self, client):
        """Test reverse geocoding with no nearby postcodes"""
        # Middle of Atlantic Ocean
        response = client.post(
            "/spatial/reverse-geocode", json={"latitude": 30.0, "longitude": -30.0}
        )
        assert response.status_code == 404

    def test_calculate_distance(self, client):
        """Test distance calculation between postcodes"""
        response = client.post(
            "/spatial/distance", json={"postcode1": "SW1A 1AA", "postcode2": "SW1A 2AA"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "distance_km" in data
        assert data["distance_km"] is not None
        assert data["distance_km"] >= 0

    def test_calculate_distance_invalid_postcode(self, client):
        """Test distance calculation with invalid postcode"""
        response = client.post(
            "/spatial/distance", json={"postcode1": "SW1A 1AA", "postcode2": "INVALID"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["distance_km"] is None
        assert "error" in data


class TestAreaEndpoints:
    """Test area-based query endpoints"""

    def test_get_area_postcodes(self, client):
        """Test getting postcodes by area"""
        response = client.get("/areas/district/Westminster?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_found" in data
        assert "area_type" in data
        assert "area_value" in data
        assert data["area_type"] == "district"
        assert data["area_value"] == "Westminster"
        assert len(data["results"]) <= 10

    def test_get_area_postcodes_invalid_type(self, client):
        """Test invalid area type"""
        response = client.get("/areas/invalid_type/Test")
        assert response.status_code == 422  # FastAPI returns 422 for validation errors
        assert "detail" in response.json()

    def test_get_outcode_postcodes(self, client):
        """Test getting postcodes by outcode"""
        response = client.get("/outcodes/SW1A")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert all(p["outcode"] == "SW1A" for p in data)

    def test_get_outcode_postcodes_not_found(self, client):
        """Test outcode not found"""
        response = client.get("/outcodes/ZZZZ")
        assert response.status_code == 404


class TestValidationAndErrors:
    """Test input validation and error handling"""

    def test_search_empty_query(self, client):
        """Test search with empty query"""
        response = client.post("/postcodes/search", json={"query": "", "limit": 5})
        assert response.status_code == 422  # Validation error

    def test_search_invalid_limit(self, client):
        """Test search with invalid limit"""
        response = client.post(
            "/postcodes/search", json={"query": "SW1A", "limit": 0}  # Should be >= 1
        )
        assert response.status_code == 422

    def test_spatial_invalid_coordinates(self, client):
        """Test spatial search with invalid coordinates"""
        response = client.post(
            "/spatial/nearest",
            json={
                "latitude": 999,  # Invalid latitude
                "longitude": 0,
                "radius_km": 1,
                "limit": 5,
            },
        )
        assert response.status_code == 422

    def test_bulk_too_many_postcodes(self, client):
        """Test bulk lookup with too many postcodes"""
        postcodes = ["SW1A 1AA"] * 101  # Exceeds max of 100
        response = client.post("/postcodes/bulk", json={"postcodes": postcodes})
        assert response.status_code == 422

    def test_parse_text_too_long(self, client):
        """Test parsing text that's too long"""
        long_text = "a" * 10001  # Exceeds max of 10000
        response = client.post(
            "/postcodes/parse", json={"text": long_text, "attempt_fix": False}
        )
        assert response.status_code == 422
