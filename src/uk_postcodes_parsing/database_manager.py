"""
Database Manager for UK Postcodes
Handles cross-platform database download and management with zero external dependencies
"""

import os
import sqlite3
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional
import hashlib
import threading
import time


class DatabaseManager:
    """Manages postcode database download and access with zero external dependencies"""

    def __init__(self, local_db_path: Optional[str] = None):
        """
        Initialize the database manager.

        Args:
            local_db_path: Optional path to a locally-built database file.
                          If provided, this database will be used instead of downloading.
        """
        # Check for environment variable override first
        env_db_path = os.environ.get("UK_POSTCODES_DB_PATH")

        if local_db_path:
            # Use the provided local database path
            self.db_path = Path(local_db_path).resolve()
            self.data_dir = self.db_path.parent
            self.is_local_db = True
        elif env_db_path:
            # Use environment variable path
            self.db_path = Path(env_db_path).resolve()
            self.data_dir = self.db_path.parent
            self.is_local_db = True
        else:
            # Use default download location
            # Cross-platform data directory
            if os.name == "nt":  # Windows
                base_dir = Path(os.environ.get("APPDATA", Path.home()))
            else:  # Unix-like systems (macOS, Linux)
                base_dir = Path.home()

            self.data_dir = base_dir / ".uk_postcodes_parsing"
            self.db_path = self.data_dir / "postcodes.db"
            self.is_local_db = False

        self.download_url = "https://github.com/angangwa/uk-postcodes-parsing/releases/latest/download/postcodes.db"
        self._download_lock = threading.Lock()

    def ensure_database(self) -> Path:
        """Ensure database exists, download if needed (thread-safe)"""
        if not self.db_path.exists():
            if self.is_local_db:
                raise FileNotFoundError(
                    f"Local database not found at: {self.db_path}\n"
                    f"Please ensure the database file exists or remove the local_db_path/UK_POSTCODES_DB_PATH setting."
                )

            with self._download_lock:
                # Double-check in case another thread downloaded it
                if not self.db_path.exists():
                    self._download_database()

        # Verify database is valid
        if not self._verify_database():
            if self.is_local_db:
                raise RuntimeError(
                    f"Local database appears corrupted: {self.db_path}\n"
                    f"Please rebuild the database or use the default download."
                )

            print("Database appears corrupted, re-downloading...")
            with self._download_lock:
                self._download_database()

        return self.db_path

    def _download_database(self):
        """Download database with simple progress indicator and retry logic"""
        if self.is_local_db:
            raise RuntimeError("Cannot download when using local database path")

        print("Downloading UK postcodes database (first time setup, ~800MB)...")
        print("This may take a few minutes depending on your connection...")

        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary file
        temp_path = self.db_path.with_suffix(".tmp")

        def progress_hook(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = min(block_num * block_size, total_size)
                percent = (downloaded / total_size) * 100
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(
                    f"\rProgress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)",
                    end="",
                )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(
                        f"\nRetrying download (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(2)  # Brief pause before retry

                start_time = time.time()
                urllib.request.urlretrieve(self.download_url, temp_path, progress_hook)

                # Move temp file to final location
                if temp_path.exists():
                    if self.db_path.exists():
                        self.db_path.unlink()  # Remove existing file
                    temp_path.rename(self.db_path)

                elapsed = time.time() - start_time
                file_size_mb = self.db_path.stat().st_size / (1024 * 1024)
                print(
                    f"\n[OK] Database download complete! ({file_size_mb:.1f} MB in {elapsed:.1f}s)"
                )
                return  # Success!

            except (urllib.error.URLError, Exception) as e:
                # Clean up temp file
                if temp_path.exists():
                    temp_path.unlink()

                if attempt < max_retries - 1:
                    # Will retry
                    print(f"\nDownload failed: {e}")
                    continue
                else:
                    # Final attempt failed
                    error_msg = (
                        f"Failed to download database after {max_retries} attempts: {e}"
                    )
                    if "404" in str(e):
                        error_msg += "\nThe database may not be available yet. Please check the GitHub releases."
                    elif "timeout" in str(e).lower() or "connection" in str(e).lower():
                        error_msg += (
                            "\nPlease check your internet connection and try again."
                        )

                    raise RuntimeError(error_msg)

    def _verify_database(self) -> bool:
        """Verify database is valid and contains expected data"""
        try:
            if not self.db_path.exists():
                return False

            # Check file size (should be substantial)
            file_size = self.db_path.stat().st_size
            if file_size < 100 * 1024 * 1024:  # Less than 100MB indicates problem
                return False

            # Try to open and query database
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            try:
                # Check if postcodes table exists and has data
                cursor = conn.execute("SELECT COUNT(*) FROM postcodes")
                count = cursor.fetchone()[0]

                # Should have over 1 million postcodes
                if count < 1000000:
                    return False

                # Test a basic query
                cursor = conn.execute("SELECT postcode FROM postcodes LIMIT 1")
                result = cursor.fetchone()
                if not result:
                    return False

                return True

            finally:
                conn.close()

        except Exception:
            return False

    def get_database_info(self) -> dict:
        """Get information about the current database"""
        if not self.db_path.exists():
            return {"exists": False, "is_local": self.is_local_db}

        try:
            file_size = self.db_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            try:
                # Get record count
                cursor = conn.execute("SELECT COUNT(*) FROM postcodes")
                record_count = cursor.fetchone()[0]

                # Try to get metadata if it exists
                metadata = {}
                try:
                    cursor = conn.execute("SELECT key, value FROM metadata")
                    metadata = {row[0]: row[1] for row in cursor.fetchall()}
                except sqlite3.OperationalError:
                    pass  # Metadata table doesn't exist

                return {
                    "exists": True,
                    "path": str(self.db_path),
                    "size_mb": round(file_size_mb, 1),
                    "record_count": record_count,
                    "metadata": metadata,
                    "is_local": self.is_local_db,
                    "source": "local" if self.is_local_db else "downloaded",
                }

            finally:
                conn.close()

        except Exception as e:
            return {"exists": True, "path": str(self.db_path), "error": str(e)}

    def remove_database(self):
        """Remove the database file (for testing or reset purposes)"""
        if self.db_path.exists():
            self.db_path.unlink()
            print(f"Removed database: {self.db_path}")


# Global instance for the module
_db_manager = None
_manager_lock = threading.Lock()


def get_database_manager(local_db_path: Optional[str] = None) -> DatabaseManager:
    """Get global database manager instance (thread-safe)

    Args:
        local_db_path: Optional path to a locally-built database file.
                      Only used when creating the first instance.
    """
    global _db_manager

    with _manager_lock:
        if _db_manager is None:
            _db_manager = DatabaseManager(local_db_path)
        elif local_db_path and str(_db_manager.db_path) != str(
            Path(local_db_path).resolve()
        ):
            # Warn if trying to change database path after initialization
            print(
                f"Warning: Database manager already initialized with {_db_manager.db_path}"
            )
            print(f"Ignoring new path: {local_db_path}")

    return _db_manager


def ensure_database(local_db_path: Optional[str] = None) -> Path:
    """Convenience function to ensure database is available

    Args:
        local_db_path: Optional path to a locally-built database file

    Returns:
        Path to the database file
    """
    return get_database_manager(local_db_path).ensure_database()


def setup_database(
    force_redownload: bool = False, local_db_path: Optional[str] = None
) -> bool:
    """
    Setup the UK postcodes database - either download or use local file

    Args:
        force_redownload: Force redownload even if database exists (ignored for local databases)
        local_db_path: Optional path to a locally-built database file to use instead of downloading

    Returns:
        bool: True if successful, False otherwise

    Example:
        >>> import uk_postcodes_parsing as ukp

        # Use default download
        >>> success = ukp.setup_database()

        # Use locally-built database
        >>> success = ukp.setup_database(local_db_path="/path/to/postcodes.db")

        # Or set environment variable
        >>> os.environ["UK_POSTCODES_DB_PATH"] = "/path/to/postcodes.db"
        >>> success = ukp.setup_database()
    """
    try:
        manager = get_database_manager(local_db_path)

        if manager.is_local_db:
            if force_redownload:
                print("Note: force_redownload is ignored when using local database")
            print(f"Using local database: {manager.db_path}")
        else:
            if force_redownload and manager.db_path.exists():
                print(f"Removing existing database for redownload...")
                manager.remove_database()
            print("Setting up UK postcodes database...")
        manager.ensure_database()

        # Verify the database is working
        info = manager.get_database_info()
        if info.get("exists") and info.get("record_count", 0) > 1000000:
            print(
                f"[OK] Database setup complete! {info['record_count']:,} postcodes available."
            )
            return True
        else:
            print("[ERROR] Database setup failed - verification failed")
            return False

    except Exception as e:
        print(f"[ERROR] Database setup failed: {e}")
        return False


def get_database_info() -> dict:
    """
    Get information about the current database status

    Returns:
        dict: Database information including size, record count, etc.

    Example:
        >>> import uk_postcodes_parsing as ukp
        >>> info = ukp.get_database_info()
        >>> print(f"Database has {info['record_count']:,} postcodes")
    """
    try:
        manager = get_database_manager()
        return manager.get_database_info()
    except Exception as e:
        return {"exists": False, "error": str(e)}
