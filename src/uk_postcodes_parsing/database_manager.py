"""
Database Manager for UK Postcodes
Handles cross-platform database download and management with zero external dependencies
"""

import os
import sqlite3
import urllib.request
import urllib.error
import urllib.parse
import lzma
import sys
import logging
from pathlib import Path
from typing import Optional
import hashlib
import threading
import time

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages postcode database download and access with zero external dependencies"""

    # Configurable minimum database size in MB (used for verification)
    MIN_DB_SIZE_MB = 50

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

        self.download_url = "https://github.com/angangwa/uk-postcodes-parsing/releases/latest/download/postcodes.db.xz"
        self._download_lock = threading.Lock()

        # Check for auto-download environment variable
        self.auto_download = os.environ.get(
            "UK_POSTCODES_AUTO_DOWNLOAD", ""
        ).lower() in ("1", "true", "yes")

    def _is_interactive_environment(self) -> bool:
        """Detect if we're in an interactive environment"""
        try:
            # Check for Jupyter/IPython
            if "ipykernel" in sys.modules or "IPython" in sys.modules:
                return True
            # Check if stdin is a TTY (terminal)
            return sys.stdin.isatty() and sys.stdout.isatty()
        except:
            return False

    def _prompt_user_for_download(self) -> bool:
        """Prompt user for download permission in interactive environments"""
        if not self._is_interactive_environment():
            return False

        try:
            print("\nUK Postcodes Database Required")
            print("=" * 40)
            print(
                "This function requires the full postcode database (~40MB compressed)."
            )
            print("This is a one-time download that will be cached locally.")
            print("")
            response = input("Download now? [y/N]: ").strip().lower()
            return response in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    def ensure_database(self) -> Path:
        """Ensure database exists, download if needed (thread-safe)"""
        if not self.db_path.exists():
            if self.is_local_db:
                raise FileNotFoundError(
                    f"Local database not found at: {self.db_path}\n"
                    f"Please ensure the database file exists or remove the local_db_path/UK_POSTCODES_DB_PATH setting."
                )

            # Check if we should auto-download or prompt user
            should_download = False
            if self.auto_download:
                should_download = True
            elif self._is_interactive_environment():
                should_download = self._prompt_user_for_download()

            if not should_download:
                # Provide helpful error message for non-interactive environments
                error_msg = (
                    "UK Postcodes database required for this operation (~40MB compressed, one-time download).\n\n"
                    "To download the database:\n"
                    "1. Run: import uk_postcodes_parsing as ukp; ukp.setup_database()\n"
                    "2. Or set environment variable: UK_POSTCODES_AUTO_DOWNLOAD=1\n"
                    "3. Or use locally built database with UK_POSTCODES_DB_PATH environment variable"
                )
                raise RuntimeError(error_msg)

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

            logger.warning("Database appears corrupted, re-downloading...")
            with self._download_lock:
                self._download_database()

        return self.db_path

    def _download_database(self):
        """Download database with simple progress indicator and retry logic"""
        if self.is_local_db:
            raise RuntimeError("Cannot download when using local database path")

        logger.info(
            "Downloading UK postcodes database (first time setup, ~40MB compressed)..."
        )
        logger.debug(
            "This will be decompressed to ~523MB locally with indices created on first use..."
        )
        logger.debug("This may take a few minutes depending on your connection...")

        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary files for compressed download and final database
        temp_compressed_path = self.db_path.with_suffix(".tmp.xz")
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
                    logger.debug(
                        f"Retrying download (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(2)  # Brief pause before retry

                start_time = time.time()

                # Validate URL scheme for security (bandit B310)
                parsed_url = urllib.parse.urlparse(self.download_url)
                if parsed_url.scheme not in ("https", "http"):
                    raise ValueError(
                        f"Unsupported URL scheme: {parsed_url.scheme}. Only HTTP(S) allowed."
                    )

                # Download compressed file
                urllib.request.urlretrieve(  # nosec B310 - URL scheme validated above
                    self.download_url, temp_compressed_path, progress_hook
                )

                download_elapsed = time.time() - start_time
                compressed_size_mb = temp_compressed_path.stat().st_size / (1024 * 1024)
                print(
                    f"\n[OK] Download complete! ({compressed_size_mb:.1f} MB in {download_elapsed:.1f}s)"
                )

                # Decompress the file
                logger.debug("Decompressing database...")
                decompress_start = time.time()

                with lzma.open(temp_compressed_path, "rb") as compressed_file:
                    with open(temp_path, "wb") as output_file:
                        # Read and write in chunks for memory efficiency
                        chunk_size = 1024 * 1024  # 1MB chunks
                        while True:
                            chunk = compressed_file.read(chunk_size)
                            if not chunk:
                                break
                            output_file.write(chunk)

                # Move decompressed file to final location
                if temp_path.exists():
                    if self.db_path.exists():
                        self.db_path.unlink()  # Remove existing file
                    temp_path.rename(self.db_path)

                # Clean up compressed temp file
                if temp_compressed_path.exists():
                    temp_compressed_path.unlink()

                decompress_elapsed = time.time() - decompress_start
                final_size_mb = self.db_path.stat().st_size / (1024 * 1024)
                print(
                    f"[OK] Decompression complete! ({final_size_mb:.1f} MB in {decompress_elapsed:.1f}s)"
                )

                # Create indices if they don't exist
                if not self._indices_exist():
                    logger.debug("Creating database indices for optimal performance...")
                    index_start = time.time()
                    self._create_indices()
                    index_elapsed = time.time() - index_start
                    logger.debug(f"[OK] Indices created in {index_elapsed:.1f}s")

                total_elapsed = time.time() - start_time
                print(f"[OK] Database setup complete! Total time: {total_elapsed:.1f}s")
                return  # Success!

            except (urllib.error.URLError, Exception) as e:
                # Clean up temp files
                if temp_compressed_path.exists():
                    temp_compressed_path.unlink()
                if temp_path.exists():
                    temp_path.unlink()

                if attempt < max_retries - 1:
                    # Will retry
                    logger.warning(f"Download failed: {e}")
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

    def _indices_exist(self) -> bool:
        """Check if database indices exist"""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            try:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
                )
                indices = cursor.fetchall()
                # We expect at least 7 custom indices
                return len(indices) >= 7
            finally:
                conn.close()
        except Exception:
            return False

    def _create_indices(self):
        """Create database indices for optimal performance"""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        try:
            # Create indices for fast lookups
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_pc_compact ON postcodes(pc_compact)",
                "CREATE INDEX IF NOT EXISTS idx_outcode ON postcodes(outcode)",
                "CREATE INDEX IF NOT EXISTS idx_incode ON postcodes(incode)",
                "CREATE INDEX IF NOT EXISTS idx_location ON postcodes(latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL",
                "CREATE INDEX IF NOT EXISTS idx_country ON postcodes(country)",
                "CREATE INDEX IF NOT EXISTS idx_district ON postcodes(district)",
                "CREATE INDEX IF NOT EXISTS idx_constituency ON postcodes(constituency)",
                "CREATE INDEX IF NOT EXISTS idx_eastings_northings ON postcodes(eastings, northings) WHERE eastings IS NOT NULL AND northings IS NOT NULL",
            ]

            for index_sql in indices:
                conn.execute(index_sql)

            conn.commit()
        finally:
            conn.close()

    def _verify_database(self) -> bool:
        """Verify database is valid and contains expected data"""
        try:
            if not self.db_path.exists():
                return False

            # Check file size (should be substantial)
            file_size = self.db_path.stat().st_size
            min_size_bytes = self.MIN_DB_SIZE_MB * 1024 * 1024
            if file_size < min_size_bytes:  # Less than minimum size indicates problem
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
            logger.debug(f"Removed database: {self.db_path}")


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
            logger.warning(
                f"Database manager already initialized with {_db_manager.db_path}"
            )
            logger.warning(f"Ignoring new path: {local_db_path}")

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
                logger.debug(
                    "Note: force_redownload is ignored when using local database"
                )
            logger.debug(f"Using local database: {manager.db_path}")
        else:
            if force_redownload and manager.db_path.exists():
                logger.debug(f"Removing existing database for redownload...")
                manager.remove_database()
            logger.debug("Setting up UK postcodes database...")
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
