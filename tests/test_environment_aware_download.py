"""Tests for environment-aware download functionality"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from uk_postcodes_parsing.database_manager import DatabaseManager
from uk_postcodes_parsing.postcode_database import lookup_postcode


class TestEnvironmentAwareDownload:
    """Test environment-aware download behavior"""

    def test_auto_download_environment_variable_enabled(self):
        """Test UK_POSTCODES_AUTO_DOWNLOAD=1 enables auto download"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"UK_POSTCODES_AUTO_DOWNLOAD": "1"}):
                manager = DatabaseManager()
                manager.data_dir = Path(temp_dir)
                manager.db_path = manager.data_dir / "postcodes.db"
                
                assert manager.auto_download is True

    def test_auto_download_environment_variable_disabled(self):
        """Test UK_POSTCODES_AUTO_DOWNLOAD=0 disables auto download"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"UK_POSTCODES_AUTO_DOWNLOAD": "0"}):
                manager = DatabaseManager()
                assert manager.auto_download is False

    def test_auto_download_environment_variable_variations(self):
        """Test various environment variable values"""
        test_cases = [
            ("1", True),
            ("true", True), 
            ("yes", True),
            ("0", False),
            ("false", False),
            ("no", False),
            ("", False),
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"UK_POSTCODES_AUTO_DOWNLOAD": env_value}):
                manager = DatabaseManager()
                assert manager.auto_download == expected

    @patch('sys.stdin.isatty')
    @patch('sys.stdout.isatty')
    def test_non_interactive_environment_error_message(self, mock_stdout_isatty, mock_stdin_isatty):
        """Test helpful error message in non-interactive environments"""
        mock_stdout_isatty.return_value = False
        mock_stdin_isatty.return_value = False
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"UK_POSTCODES_AUTO_DOWNLOAD": "0"}):
                manager = DatabaseManager()
                manager.data_dir = Path(temp_dir)
                manager.db_path = manager.data_dir / "postcodes.db"
                
                with pytest.raises(RuntimeError) as exc_info:
                    manager.ensure_database()
                
                error_msg = str(exc_info.value)
                assert "UK Postcodes database required" in error_msg
                assert "setup_database()" in error_msg
                assert "UK_POSTCODES_AUTO_DOWNLOAD=1" in error_msg

    @patch('uk_postcodes_parsing.postcode_database.get_database')
    def test_database_error_propagation_in_api_functions(self, mock_get_database):
        """Test that helpful database errors are propagated through API functions"""
        mock_db = MagicMock()
        mock_db.lookup.side_effect = RuntimeError(
            "UK Postcodes database required for this operation"
        )
        mock_get_database.return_value = mock_db
        
        with pytest.raises(RuntimeError, match="UK Postcodes database required"):
            lookup_postcode("SW1A 1AA")