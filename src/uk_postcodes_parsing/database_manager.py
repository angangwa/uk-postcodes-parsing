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
    
    def __init__(self):
        # Cross-platform data directory
        if os.name == 'nt':  # Windows
            base_dir = Path(os.environ.get('APPDATA', Path.home()))
        else:  # Unix-like systems (macOS, Linux)
            base_dir = Path.home()
        
        self.data_dir = base_dir / '.uk_postcodes_parsing'
        self.db_path = self.data_dir / 'postcodes.db'
        self.download_url = 'https://github.com/angangwa/uk-postcodes-parsing/releases/latest/download/postcodes.db'
        self._download_lock = threading.Lock()
        
    def ensure_database(self) -> Path:
        """Ensure database exists, download if needed (thread-safe)"""
        if not self.db_path.exists():
            with self._download_lock:
                # Double-check in case another thread downloaded it
                if not self.db_path.exists():
                    self._download_database()
        
        # Verify database is valid
        if not self._verify_database():
            print("Database appears corrupted, re-downloading...")
            with self._download_lock:
                self._download_database()
        
        return self.db_path
    
    def _download_database(self):
        """Download database with simple progress indicator"""
        print("Downloading UK postcodes database (first time setup, ~1GB)...")
        print("This may take a few minutes depending on your connection...")
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temporary file
        temp_path = self.db_path.with_suffix('.tmp')
        
        def progress_hook(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = min(block_num * block_size, total_size)
                percent = (downloaded / total_size) * 100
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\rProgress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="")
        
        try:
            start_time = time.time()
            urllib.request.urlretrieve(self.download_url, temp_path, progress_hook)
            
            # Move temp file to final location
            if temp_path.exists():
                if self.db_path.exists():
                    self.db_path.unlink()  # Remove existing file
                temp_path.rename(self.db_path)
            
            elapsed = time.time() - start_time
            file_size_mb = self.db_path.stat().st_size / (1024 * 1024)
            print(f"\n✅ Database download complete! ({file_size_mb:.1f} MB in {elapsed:.1f}s)")
            
        except urllib.error.URLError as e:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            
            error_msg = f"Failed to download database: {e}"
            if "404" in str(e):
                error_msg += "\nThe database may not be available yet. Please check the GitHub releases."
            elif "timeout" in str(e).lower() or "connection" in str(e).lower():
                error_msg += "\nPlease check your internet connection and try again."
            
            raise RuntimeError(error_msg)
        
        except Exception as e:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Unexpected error during download: {e}")
    
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
            return {"exists": False}
        
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
                    "metadata": metadata
                }
                
            finally:
                conn.close()
                
        except Exception as e:
            return {
                "exists": True,
                "path": str(self.db_path),
                "error": str(e)
            }
    
    def remove_database(self):
        """Remove the database file (for testing or reset purposes)"""
        if self.db_path.exists():
            self.db_path.unlink()
            print(f"Removed database: {self.db_path}")


# Global instance for the module
_db_manager = None
_manager_lock = threading.Lock()


def get_database_manager() -> DatabaseManager:
    """Get global database manager instance (thread-safe)"""
    global _db_manager
    
    with _manager_lock:
        if _db_manager is None:
            _db_manager = DatabaseManager()
    
    return _db_manager


def ensure_database() -> Path:
    """Convenience function to ensure database is available"""
    return get_database_manager().ensure_database()