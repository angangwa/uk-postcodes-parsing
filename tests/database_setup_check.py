#!/usr/bin/env python3
"""
Cross-platform database setup test script for GitHub Actions
"""
import uk_postcodes_parsing as ukp
import os
import sys

def main():
    print(f"OS: {os.name}")
    print(f"Platform: {sys.platform}")
    
    try:
        success = ukp.setup_database()
        print(f"Database setup: {success}")
        
        if success:
            info = ukp.get_database_info()
            print(f"Database path: {info.get('path', 'unknown')}")
            print(f"Records: {info.get('record_count', 'unknown')}")
            print(f"Size: {info.get('size_mb', 'unknown')}MB")
            print("Database setup completed successfully!")
        else:
            print("Database setup failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"Database setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()