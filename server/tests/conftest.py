"""
Test configuration and fixtures for FastAPI server tests
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path to import the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def sample_postcodes():
    """Sample postcodes for testing"""
    return {
        "valid": ["SW1A 1AA", "SW1A 2AA", "E1 6AN", "EH1 1AD"],
        "invalid": ["INVALID", "XXX XXX", "12345"],
        "mixed_case": ["sw1a 1aa", "SW1A1AA", " SW1A 1AA "],
    }


@pytest.fixture
def sample_coordinates():
    """Sample coordinates for testing"""
    return {
        "parliament": {"latitude": 51.5014, "longitude": -0.1419},
        "edinburgh": {"latitude": 55.9533, "longitude": -3.1883},
        "invalid": {"latitude": 999, "longitude": 999},
    }


@pytest.fixture
def sample_text():
    """Sample text containing postcodes"""
    return {
        "simple": "Please send mail to SW1A 1AA or SW1A 2AA",
        "with_ocr_errors": "Send to SW1A OAA (O instead of 0) or E1 6AN",
        "no_postcodes": "This text contains no valid postcodes at all",
        "mixed": "Valid: SW1A 1AA, Invalid: XXX XXX, OCR: SW1A OAA",
    }
