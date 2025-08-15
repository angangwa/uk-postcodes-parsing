"""Tests for outcode-based validation system"""

import importlib
import pytest

from uk_postcodes_parsing.ukpostcode import is_in_ons_postcode_directory


class TestOutcodeValidation:
    """Test outcode-based postcode validation"""

    def test_outcode_validation_without_database_dependency(self):
        """Test that postcode validation works without requiring database"""
        # These should work using outcode files, not requiring database download
        result_valid = is_in_ons_postcode_directory("SW1A 1AA")
        result_invalid = is_in_ons_postcode_directory("FAKE 123")
        
        assert isinstance(result_valid, bool)
        assert isinstance(result_invalid, bool)
        # SW1A 1AA should exist, FAKE 123 should not
        assert result_valid is True
        assert result_invalid is False

    def test_known_valid_postcodes(self):
        """Test validation of known valid postcodes"""
        valid_postcodes = [
            "SW1A 1AA",  # House of Commons
            "E1 6AN",    # London postcode
        ]
        
        for postcode in valid_postcodes:
            result = is_in_ons_postcode_directory(postcode)
            assert result is True, f"Expected {postcode} to be valid"

    def test_known_invalid_postcodes(self):
        """Test validation of known invalid postcodes"""
        invalid_postcodes = [
            "E1 9AB",    # Same outcode as valid one, but invalid incode
            "M1 1AA",    # Valid format but doesn't exist
            "ZZ1 1ZZ",   # Valid format but fake postcode
            "FAKE 123",  # Invalid format
            "INVALID",   # Not valid postcode format at all
        ]
        
        for postcode in invalid_postcodes:
            result = is_in_ons_postcode_directory(postcode)
            assert result is False, f"Expected {postcode} to be invalid"

    def test_case_insensitive_outcode_lookup(self):
        """Test that outcode lookup is case insensitive"""
        test_cases = [
            "SW1A 1AA",
            "sw1a 1aa", 
            "Sw1a 1Aa",
            "SW1a 1aa",
        ]
        
        results = [is_in_ons_postcode_directory(pc) for pc in test_cases]
        # All should return the same result (True for SW1A 1AA)
        assert all(r == results[0] for r in results)
        assert all(r is True for r in results)

    def test_outcode_dynamic_import_mechanism(self):
        """Test that outcode modules can be imported dynamically"""
        # Test importing a known outcode module
        try:
            module = importlib.import_module("uk_postcodes_parsing.outcodes.sw1a")
            incodes = getattr(module, 'INCODES', set())
            assert isinstance(incodes, set)
            assert len(incodes) > 0
            assert "1AA" in incodes  # SW1A 1AA should exist
        except ImportError:
            pytest.skip("SW1A outcode module not available (expected in test environment)")

    def test_outcode_graceful_failure_for_missing_outcodes(self):
        """Test graceful handling when outcode module doesn't exist"""
        # Try to validate a postcode with a non-existent outcode
        result = is_in_ons_postcode_directory("ZZ9 9ZZ")
        assert result is False  # Should return False, not crash

    def test_invalid_postcode_format_handling(self):
        """Test handling of invalid postcode formats"""
        invalid_formats = [
            "",           # Empty string
            "A",          # Too short
            "ABCDEFGHIJ", # Too long
            "123 456",    # All numbers
            "ABC DEF",    # All letters
        ]
        
        for invalid_pc in invalid_formats:
            result = is_in_ons_postcode_directory(invalid_pc)
            assert result is False, f"Expected invalid format '{invalid_pc}' to return False"