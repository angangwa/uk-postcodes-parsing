"""
Test database management functionality
Tests cross-platform paths, download, verification, and error handling
"""

import os
import pytest
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error

from uk_postcodes_parsing.database_manager import (
    DatabaseManager,
    get_database_manager,
    setup_database,
    get_database_info,
)


@pytest.fixture(autouse=True)
def reset_global_manager():
    """Reset global database manager before and after each test to prevent test pollution"""
    import uk_postcodes_parsing.database_manager as dm
    # Store original state
    original_manager = dm._db_manager
    dm._db_manager = None
    
    yield  # Run the test
    
    # Restore to None to ensure clean state for next test
    dm._db_manager = None


class TestDatabaseManager:
    """Test DatabaseManager class functionality"""

    def test_cross_platform_paths(self):
        """Test cross-platform data directory handling"""
        manager = DatabaseManager()

        # Test that data directory is created properly
        if os.name == "nt":  # Windows
            assert "AppData" in str(manager.data_dir) or str(
                manager.data_dir
            ).startswith(str(Path.home()))
        else:  # Unix-like
            assert str(manager.data_dir).startswith(str(Path.home()))

        # Test database path
        assert manager.db_path.name == "postcodes.db"
        assert manager.db_path.parent == manager.data_dir

    def test_singleton_pattern(self):
        """Test that get_database_manager returns same instance"""
        manager1 = get_database_manager()
        manager2 = get_database_manager()
        assert manager1 is manager2

    def test_thread_safe_singleton(self):
        """Test thread-safe singleton creation"""
        managers = []

        def create_manager():
            managers.append(get_database_manager())

        threads = [threading.Thread(target=create_manager) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should be the same instance
        assert all(m is managers[0] for m in managers)

    @patch("urllib.request.urlretrieve")
    def test_download_success(self, mock_urlretrieve):
        """Test successful database download"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseManager()
            manager.data_dir = Path(temp_dir)
            manager.db_path = manager.data_dir / "postcodes.db"

            # Create a mock database file
            temp_db = Path(temp_dir) / "postcodes.db.tmp"
            temp_db.write_bytes(b"x" * (200 * 1024 * 1024))  # 200MB mock file

            def mock_download(url, path, hook=None):
                if hook:
                    hook(
                        1, 1024 * 1024, 200 * 1024 * 1024
                    )  # Simulate download progress
                # Move temp file to final location
                Path(path).write_bytes(temp_db.read_bytes())

            mock_urlretrieve.side_effect = mock_download

            manager._download_database()

            assert manager.db_path.exists()
            assert manager.db_path.stat().st_size > 100 * 1024 * 1024

    @patch("urllib.request.urlretrieve")
    def test_download_network_error(self, mock_urlretrieve):
        """Test download failure handling"""
        mock_urlretrieve.side_effect = urllib.error.URLError("Network error")

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseManager()
            manager.data_dir = Path(temp_dir)
            manager.db_path = manager.data_dir / "postcodes.db"

            with pytest.raises(RuntimeError, match="Failed to download database"):
                manager._download_database()

    @patch("urllib.request.urlretrieve")
    def test_download_404_error(self, mock_urlretrieve):
        """Test 404 error with helpful message"""
        mock_urlretrieve.side_effect = urllib.error.HTTPError(
            "http://test.com", 404, "Not Found", {}, None
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseManager()
            manager.data_dir = Path(temp_dir)
            manager.db_path = manager.data_dir / "postcodes.db"

            with pytest.raises(RuntimeError, match="database may not be available"):
                manager._download_database()

    def test_database_verification(self):
        """Test database file verification"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseManager()
            manager.data_dir = Path(temp_dir)
            manager.db_path = manager.data_dir / "postcodes.db"

            # Test non-existent file
            assert not manager._verify_database()

            # Test too small file
            manager.db_path.write_bytes(b"small file")
            assert not manager._verify_database()

            # Test file that looks like database but isn't
            manager.db_path.write_bytes(b"x" * (200 * 1024 * 1024))
            assert not manager._verify_database()

    @patch("sqlite3.connect")
    def test_database_verification_with_valid_db(self, mock_connect):
        """Test verification with valid database structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseManager()
            manager.data_dir = Path(temp_dir)
            manager.db_path = manager.data_dir / "postcodes.db"

            # Create a file large enough
            manager.db_path.write_bytes(b"x" * (200 * 1024 * 1024))

            # Mock database connection
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.side_effect = [
                (1500000,),
                ("SW1A 1AA",),
            ]  # Count, sample postcode
            mock_conn.execute.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            assert manager._verify_database()

            # Verify SQL queries were called
            assert mock_conn.execute.call_count >= 2

    def test_remove_database(self):
        """Test database removal"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseManager()
            manager.data_dir = Path(temp_dir)
            manager.db_path = manager.data_dir / "postcodes.db"

            # Create database file
            manager.db_path.write_text("test")
            assert manager.db_path.exists()

            # Remove it
            manager.remove_database()
            assert not manager.db_path.exists()

    def test_get_database_info_missing(self):
        """Test database info when database doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseManager()
            manager.data_dir = Path(temp_dir)
            manager.db_path = manager.data_dir / "postcodes.db"

            info = manager.get_database_info()
            assert info["exists"] is False

    @patch("sqlite3.connect")
    def test_get_database_info_valid(self, mock_connect):
        """Test database info with valid database"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DatabaseManager()
            manager.data_dir = Path(temp_dir)
            manager.db_path = manager.data_dir / "postcodes.db"

            # Create database file
            manager.db_path.write_bytes(b"x" * (800 * 1024 * 1024))  # 800MB

            # Mock database connection
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (1799395,)  # Expected postcode count
            mock_cursor.fetchall.return_value = [("version", "2.0"), ("date", "2024")]
            mock_conn.execute.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            info = manager.get_database_info()

            assert info["exists"] is True
            assert info["record_count"] == 1799395
            assert info["size_mb"] == 800.0
            assert "metadata" in info


class TestSetupFunctions:
    """Test module-level setup functions"""

    @patch("uk_postcodes_parsing.database_manager.get_database_manager")
    def test_setup_database_success(self, mock_get_manager):
        """Test successful database setup"""
        mock_manager = MagicMock()
        mock_manager.db_path.exists.return_value = False
        mock_manager.get_database_info.return_value = {
            "exists": True,
            "record_count": 1799395,
        }
        mock_get_manager.return_value = mock_manager

        result = setup_database()

        assert result is True
        mock_manager.ensure_database.assert_called_once()

    @patch("uk_postcodes_parsing.database_manager.get_database_manager")
    def test_setup_database_force_redownload(self, mock_get_manager):
        """Test forced redownload for downloaded databases"""
        mock_manager = MagicMock()
        mock_manager.db_path.exists.return_value = True
        mock_manager.is_local_db = False  # Explicitly test downloaded database scenario
        mock_manager.get_database_info.return_value = {
            "exists": True,
            "record_count": 1799395,
        }
        mock_get_manager.return_value = mock_manager

        result = setup_database(force_redownload=True)

        assert result is True
        mock_manager.remove_database.assert_called_once()
        mock_manager.ensure_database.assert_called_once()

    @patch("uk_postcodes_parsing.database_manager.get_database_manager")
    def test_setup_database_failure(self, mock_get_manager):
        """Test setup failure handling"""
        mock_manager = MagicMock()
        mock_manager.ensure_database.side_effect = RuntimeError("Download failed")
        mock_get_manager.return_value = mock_manager

        result = setup_database()

        assert result is False

    @patch("uk_postcodes_parsing.database_manager.get_database_manager")
    def test_get_database_info_function(self, mock_get_manager):
        """Test get_database_info function"""
        mock_manager = MagicMock()
        expected_info = {"exists": True, "record_count": 1799395}
        mock_manager.get_database_info.return_value = expected_info
        mock_get_manager.return_value = mock_manager

        info = get_database_info()

        assert info == expected_info

    @patch("uk_postcodes_parsing.database_manager.get_database_manager")
    def test_get_database_info_error(self, mock_get_manager):
        """Test get_database_info error handling"""
        mock_get_manager.side_effect = Exception("Connection error")

        info = get_database_info()

        assert info["exists"] is False
        assert "error" in info

    @patch("uk_postcodes_parsing.database_manager._manager_lock")
    @patch("uk_postcodes_parsing.database_manager.DatabaseManager")
    def test_setup_database_with_local_path(self, mock_db_class, mock_lock):
        """Test setup with local database path"""
        # Setup mock database manager
        mock_manager = MagicMock()
        mock_manager.is_local_db = True
        mock_manager.db_path = Path("/path/to/local.db")
        mock_manager.ensure_database.return_value = Path("/path/to/local.db")
        mock_manager.get_database_info.return_value = {
            "exists": True,
            "record_count": 1799395,
            "is_local": True,
            "source": "local"
        }
        mock_db_class.return_value = mock_manager
        
        result = setup_database(local_db_path="/path/to/local.db")
        
        assert result is True
        mock_db_class.assert_called_once_with("/path/to/local.db")
        mock_manager.ensure_database.assert_called_once()

    @patch("uk_postcodes_parsing.database_manager.get_database_manager")
    def test_setup_database_local_ignores_force_redownload(self, mock_get_manager):
        """Test that force_redownload is ignored for local databases"""
        mock_manager = MagicMock()
        mock_manager.is_local_db = True
        mock_manager.db_path = Path("/path/to/local.db")
        mock_manager.get_database_info.return_value = {
            "exists": True,
            "record_count": 1799395,
            "is_local": True,
        }
        mock_get_manager.return_value = mock_manager
        
        result = setup_database(force_redownload=True)
        
        assert result is True
        # remove_database should NOT be called for local databases
        mock_manager.remove_database.assert_not_called()
        mock_manager.ensure_database.assert_called_once()

    @patch.dict(os.environ, {"UK_POSTCODES_DB_PATH": "/env/path/postcodes.db"})
    @patch("uk_postcodes_parsing.database_manager.Path")
    def test_database_manager_env_variable(self, mock_path_class):
        """Test DatabaseManager uses environment variable"""
        mock_path = MagicMock()
        mock_path.resolve.return_value = Path("/env/path/postcodes.db")
        mock_path.parent = Path("/env/path")
        mock_path_class.return_value = mock_path
        
        from uk_postcodes_parsing.database_manager import DatabaseManager
        
        manager = DatabaseManager()
        
        assert manager.is_local_db is True
        mock_path_class.assert_called_with("/env/path/postcodes.db")

    def test_database_manager_local_path_priority(self):
        """Test that local_db_path takes priority over environment variable"""
        with patch.dict(os.environ, {"UK_POSTCODES_DB_PATH": "/env/path/postcodes.db"}):
            from uk_postcodes_parsing.database_manager import DatabaseManager
            
            manager = DatabaseManager(local_db_path="/local/path/postcodes.db")
            
            assert manager.is_local_db is True
            assert str(manager.db_path) == str(Path("/local/path/postcodes.db").resolve())

    def test_ensure_database_local_not_found(self):
        """Test error when local database doesn't exist"""
        from uk_postcodes_parsing.database_manager import DatabaseManager
        
        manager = DatabaseManager(local_db_path="/nonexistent/database.db")
        
        with pytest.raises(FileNotFoundError, match="Local database not found"):
            manager.ensure_database()

    @patch("uk_postcodes_parsing.database_manager.DatabaseManager._verify_database")
    def test_ensure_database_local_corrupted(self, mock_verify):
        """Test error when local database is corrupted"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"corrupted data")
        
        try:
            from uk_postcodes_parsing.database_manager import DatabaseManager
            
            mock_verify.return_value = False  # Database verification fails
            manager = DatabaseManager(local_db_path=tmp_path)
            
            with pytest.raises(RuntimeError, match="Local database appears corrupted"):
                manager.ensure_database()
        finally:
            os.unlink(tmp_path)
