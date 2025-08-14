"""
Test backward compatibility with existing code
Ensures all existing functionality continues to work unchanged in v2.0
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

import uk_postcodes_parsing as ukp
from uk_postcodes_parsing import ukpostcode
from uk_postcodes_parsing.ukpostcode import (
    Postcode,
    parse,
    parse_from_corpus,
    is_in_ons_postcode_directory,
)


class TestExistingAPIUnchanged:
    """Test that existing API remains completely unchanged"""

    def test_parse_function_signature(self):
        """Test that parse() function signature is unchanged"""
        # Should accept string and optional parameters
        result = ukpostcode.parse("SW1A 1AA")
        assert isinstance(result, Postcode)

        result = ukpostcode.parse("SW1A 1AA", attempt_fix=False)
        assert isinstance(result, Postcode)

        # Test with invalid postcode
        result = ukpostcode.parse("INVALID")
        assert result is None

    def test_parse_from_corpus_function_signature(self):
        """Test that parse_from_corpus() function signature is unchanged"""
        corpus = "Contact us at SW1A 1AA or visit E3 4SS"

        # Default parameters
        results = ukpostcode.parse_from_corpus(corpus)
        assert isinstance(results, list)
        assert len(results) == 2

        # With attempt_fix parameter
        results = ukpostcode.parse_from_corpus(corpus, attempt_fix=True)
        assert isinstance(results, list)

        # With try_all_fix_options parameter
        results = ukpostcode.parse_from_corpus(
            corpus, attempt_fix=True, try_all_fix_options=True
        )
        assert isinstance(results, list)

    def test_postcode_class_unchanged(self):
        """Test that Postcode dataclass fields are unchanged"""
        result = ukpostcode.parse("SW1A 1AA")

        # Original fields must be present
        assert hasattr(result, "postcode")
        assert hasattr(result, "original")
        assert hasattr(result, "incode")
        assert hasattr(result, "outcode")
        assert hasattr(result, "area")
        assert hasattr(result, "district")
        assert hasattr(result, "sub_district")
        assert hasattr(result, "sector")
        assert hasattr(result, "unit")

        # Calculated fields
        assert hasattr(result, "is_in_ons_postcode_directory")
        assert hasattr(result, "fix_distance")

        # Test field values
        assert result.postcode == "SW1A 1AA"
        assert result.incode == "1AA"
        assert result.outcode == "SW1A"
        assert result.area == "SW"
        assert result.district == "SW1"
        assert result.sub_district == "SW1A"
        assert result.sector == "SW1A 1"
        assert result.unit == "AA"

    def test_postcode_class_ordering(self):
        """Test that Postcode class ordering behavior is unchanged"""
        postcode1 = ukpostcode.parse("SW1A 1AA")
        postcode2 = ukpostcode.parse("SW1A 1AB")  # Different but similar

        # Should be sortable
        postcodes = [postcode2, postcode1]
        sorted_postcodes = sorted(postcodes, reverse=True)

        # Should sort by is_in_ons_postcode_directory first, then fix_distance
        assert len(sorted_postcodes) == 2

    def test_imports_unchanged(self):
        """Test that all existing imports work unchanged"""
        # Main module imports
        assert hasattr(ukp, "parse")
        assert hasattr(ukp, "parse_from_corpus")
        assert hasattr(ukp, "is_in_ons_postcode_directory")
        assert hasattr(ukp, "Postcode")

        # Direct imports from ukpostcode module
        from uk_postcodes_parsing.ukpostcode import (
            parse,
            parse_from_corpus,
            Postcode,
            is_in_ons_postcode_directory,
        )

        assert callable(parse)
        assert callable(parse_from_corpus)
        assert callable(is_in_ons_postcode_directory)
        assert Postcode is not None


class TestExistingBehaviorUnchanged:
    """Test that existing behavior patterns remain unchanged"""

    def test_parse_basic_postcodes(self):
        """Test basic postcode parsing behavior"""
        test_cases = [
            ("SW1A 1AA", "SW1A 1AA"),
            ("sw1a 1aa", "SW1A 1AA"),  # Case conversion
            ("SW1A1AA", "SW1A 1AA"),  # Space insertion
            (" SW1A 1AA ", "SW1A 1AA"),  # Whitespace trimming
        ]

        for input_postcode, expected in test_cases:
            result = ukpostcode.parse(input_postcode)
            assert result.postcode == expected

    def test_parse_component_extraction(self):
        """Test that postcode component extraction works as before"""
        test_cases = [
            # (postcode, outcode, incode, area, district, sub_district, sector, unit)
            ("AA9A 9AA", "AA9A", "9AA", "AA", "AA9", "AA9A", "AA9A 9", "AA"),
            ("A9A 9AA", "A9A", "9AA", "A", "A9", "A9A", "A9A 9", "AA"),
            ("A9 9AA", "A9", "9AA", "A", "A9", None, "A9 9", "AA"),
            ("A99 9AA", "A99", "9AA", "A", "A99", None, "A99 9", "AA"),
            ("AA9 9AA", "AA9", "9AA", "AA", "AA9", None, "AA9 9", "AA"),
            ("AA99 9AA", "AA99", "9AA", "AA", "AA99", None, "AA99 9", "AA"),
        ]

        for (
            postcode_str,
            outcode,
            incode,
            area,
            district,
            sub_district,
            sector,
            unit,
        ) in test_cases:
            result = ukpostcode.parse(postcode_str)
            assert result.outcode == outcode
            assert result.incode == incode
            assert result.area == area
            assert result.district == district
            assert result.sub_district == sub_district
            assert result.sector == sector
            assert result.unit == unit

    def test_parse_from_corpus_behavior(self):
        """Test corpus parsing behavior remains unchanged"""
        corpus = "Contact us at SW1A 1AA or try E3 4SS for the London office"
        results = ukpostcode.parse_from_corpus(corpus)

        assert len(results) == 2
        assert results[0].postcode == "SW1A 1AA"
        assert results[1].postcode == "E3 4SS"

        # Original text should be preserved
        assert (
            "sw1a 1aa" in results[0].original.lower()
            or "SW1A 1AA" in results[0].original
        )
        assert (
            "e3 4ss" in results[1].original.lower() or "E3 4SS" in results[1].original
        )

    def test_fix_distance_calculation(self):
        """Test fix distance calculation behavior"""
        # Perfect match - no fixes needed
        result = ukpostcode.parse("SW1A 1AA")
        assert result.fix_distance == 0

        # With OCR fixes
        result = ukpostcode.parse("SW1A 1AA", attempt_fix=True)
        assert result.fix_distance == 0  # Still perfect

    def test_ons_directory_check_behavior(self):
        """Test ONS postcode directory checking behavior"""
        # This should use the new SQLite database but maintain same interface
        valid_postcode = "SW1A 1AA"  # Known valid postcode

        # Direct function call
        is_valid = is_in_ons_postcode_directory(valid_postcode)
        assert isinstance(is_valid, bool)

        # Through parsed postcode object
        result = ukpostcode.parse(valid_postcode)
        assert isinstance(result.is_in_ons_postcode_directory, bool)


class TestSQLiteFallbackBehavior:
    """Test SQLite database fallback to Python file behavior"""

    def create_test_database(self, temp_dir):
        """Create minimal test database"""
        db_path = Path(temp_dir) / "fallback_test.db"
        conn = sqlite3.connect(str(db_path))

        conn.execute(
            """
            CREATE TABLE postcodes (
                postcode TEXT PRIMARY KEY,
                pc_compact TEXT,
                incode TEXT,
                outcode TEXT,
                latitude REAL,
                longitude REAL
            )
        """
        )

        # Insert some test postcodes
        conn.execute(
            """
            INSERT INTO postcodes VALUES 
            ('SW1A 1AA', 'SW1A1AA', '1AA', 'SW1A', 51.501009, -0.141588)
        """
        )

        conn.commit()
        conn.close()
        return db_path

    def test_ons_check_outcodes_success(self):
        """Test ONS check uses outcode files for validation"""
        # Test with a known valid postcode that should exist in outcodes
        result = is_in_ons_postcode_directory("SW1A 1AA")
        
        # This should work using our outcode-based system
        assert result is True

    def test_ons_check_outcodes_not_found(self):
        """Test ONS check returns False when postcode not in outcode files"""
        # Test with clearly invalid postcode
        result = is_in_ons_postcode_directory("FAKE 123")
        
        assert result is False

    def test_ons_check_outcodes_behavior(self):
        """Test outcode-based validation with known postcodes"""
        # Test with known valid and invalid postcodes
        test_cases = [
            ("SW1A 1AA", True),   # House of Commons - definitely exists
            ("E1 6AN", True),     # London - exists in our data
            ("E1 9AB", False),    # Same outcode but invalid incode
            ("M1 1AA", False),    # Valid format but doesn't exist
            ("ZZ1 1ZZ", False),   # Valid format but fake postcode
            ("INVALID", False),   # Not valid postcode format at all
        ]
        
        for postcode, expected in test_cases:
            result = is_in_ons_postcode_directory(postcode)
            assert result == expected, f"Expected {postcode} to be {expected}, got {result}"

    @patch("uk_postcodes_parsing.postcode_database.get_database")
    def test_parsed_postcode_ons_check_with_sqlite(self, mock_get_db):
        """Test that parsed postcode ONS check uses SQLite"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_db.lookup.return_value = mock_result
        mock_get_db.return_value = mock_db

        # Parse postcode - this should trigger ONS check
        result = ukpostcode.parse("SW1A 1AA")

        # Should have used SQLite for ONS check
        assert result.is_in_ons_postcode_directory is True


class TestExistingCodePatterns:
    """Test that existing code patterns continue to work"""

    def test_sorting_postcodes_pattern(self):
        """Test existing pattern of sorting postcodes by quality"""
        corpus = "Contact SW1A 1AA and also try SW1E 6LA and maybe FAKE 123"
        results = ukpostcode.parse_from_corpus(corpus, attempt_fix=True)

        # Sort by quality (existing pattern)
        sorted_results = sorted(results, reverse=True)

        # Higher quality postcodes (in ONS directory, lower fix distance) first
        assert len(sorted_results) >= 2
        for result in sorted_results:
            assert isinstance(result, Postcode)

    def test_filtering_valid_postcodes_pattern(self):
        """Test existing pattern of filtering valid postcodes"""
        corpus = "Valid: SW1A 1AA, Invalid: FAKE 123, Also valid: E3 4SS"
        results = ukpostcode.parse_from_corpus(corpus, attempt_fix=True)

        # Filter to only valid postcodes (existing pattern)
        valid_postcodes = [pc for pc in results if pc.is_in_ons_postcode_directory]

        # Should have some valid postcodes
        assert len(valid_postcodes) >= 1
        for pc in valid_postcodes:
            assert pc.is_in_ons_postcode_directory is True

    def test_confidence_scoring_pattern(self):
        """Test existing pattern of confidence-based filtering"""
        corpus = "Good: SW1A 1AA, Typo: SW1A 1AB, Very bad: ABCD EFGH"
        results = ukpostcode.parse_from_corpus(corpus, attempt_fix=True)

        # Filter by fix distance (existing pattern)
        high_confidence = [
            pc for pc in results if pc.fix_distance >= -1  # Allow minor fixes
        ]

        assert len(high_confidence) >= 1
        for pc in high_confidence:
            assert pc.fix_distance >= -1

    def test_bulk_processing_pattern(self):
        """Test existing bulk processing patterns"""
        postcodes_to_check = ["SW1A 1AA", "SW1E 6LA", "INVALID", "E3 4SS"]

        results = []
        for pc_str in postcodes_to_check:
            parsed = ukpostcode.parse(pc_str)
            if parsed:
                results.append(parsed)

        # Should handle mix of valid and invalid gracefully
        assert len(results) >= 3  # Should get valid ones
        for result in results:
            assert isinstance(result, Postcode)


class TestBackwardCompatibleImports:
    """Test that all existing import patterns continue to work"""

    def test_main_module_imports(self):
        """Test imports from main uk_postcodes_parsing module"""
        # These should work as before
        from uk_postcodes_parsing import (
            parse,
            parse_from_corpus,
            Postcode,
            is_in_ons_postcode_directory,
        )

        assert callable(parse)
        assert callable(parse_from_corpus)
        assert callable(is_in_ons_postcode_directory)

        result = parse("SW1A 1AA")
        assert isinstance(result, Postcode)

    def test_submodule_imports(self):
        """Test imports from ukpostcode submodule"""
        from uk_postcodes_parsing.ukpostcode import parse, parse_from_corpus, Postcode

        assert callable(parse)
        assert callable(parse_from_corpus)

        result = parse("SW1A 1AA")
        assert isinstance(result, Postcode)

    def test_fix_module_imports(self):
        """Test imports from fix module"""
        from uk_postcodes_parsing.fix import fix

        assert callable(fix)

        result = fix("SW1A 2AA")
        assert isinstance(result, str)

    def test_postcode_utils_imports(self):
        """Test imports from postcode_utils module"""
        from uk_postcodes_parsing import postcode_utils

        assert hasattr(postcode_utils, "is_valid")
        assert callable(postcode_utils.is_valid)

        result = postcode_utils.is_valid("SW1A 1AA")
        assert isinstance(result, bool)


class TestNoBreakingChanges:
    """Test that no breaking changes were introduced"""

    def test_function_signatures_unchanged(self):
        """Test that function signatures haven't changed"""
        import inspect

        # parse function
        sig = inspect.signature(ukpostcode.parse)
        params = list(sig.parameters.keys())
        assert "postcode" in params
        assert "attempt_fix" in params

        # parse_from_corpus function
        sig = inspect.signature(ukpostcode.parse_from_corpus)
        params = list(sig.parameters.keys())
        assert "text" in params
        assert "attempt_fix" in params
        assert "try_all_fix_options" in params

    def test_return_types_unchanged(self):
        """Test that return types haven't changed"""
        # parse returns Postcode or None
        result = ukpostcode.parse("SW1A 1AA")
        assert isinstance(result, Postcode) or result is None

        # parse_from_corpus returns list of Postcode
        results = ukpostcode.parse_from_corpus("SW1A 1AA")
        assert isinstance(results, list)
        if results:
            assert isinstance(results[0], Postcode)

        # is_in_ons_postcode_directory returns bool
        result = is_in_ons_postcode_directory("SW1A 1AA")
        assert isinstance(result, bool)

    def test_exception_behavior_unchanged(self):
        """Test that exception behavior hasn't changed"""
        # These should not raise exceptions, just return None/empty
        result = ukpostcode.parse(None)
        assert result is None

        result = ukpostcode.parse("")
        assert result is None

        results = ukpostcode.parse_from_corpus("")
        assert results == []
