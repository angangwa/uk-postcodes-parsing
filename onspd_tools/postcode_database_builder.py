#!/usr/bin/env python3
"""
SQLite Database Creator for Enhanced UK Postcodes
Creates an efficient SQLite database from ONSPD data
Based on postcodes.io extraction logic (MIT License)
"""

import sqlite3
import pandas as pd
import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from onspd_processor import ONSPDProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostcodeSQLiteCreator:
    """Create SQLite database from ONSPD data with proper schema and indexes"""
    
    def __init__(self, data_dir: str = "../data"):
        self.data_dir = Path(data_dir)
        self.processor = ONSPDProcessor(data_dir)
        
    def create_database_schema(self, db_path: str):
        """Create SQLite database with optimized schema"""
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA journal_mode=WAL')  # Better concurrency
        conn.execute('PRAGMA synchronous=NORMAL')  # Better performance
        conn.execute('PRAGMA cache_size=10000')  # 10MB cache
        
        # Drop existing tables
        conn.execute('DROP TABLE IF EXISTS postcodes')
        conn.execute('DROP TABLE IF EXISTS metadata')
        
        # Create streamlined postcodes table (22 essential columns vs 42)
        conn.execute('''
        CREATE TABLE postcodes (
            postcode TEXT PRIMARY KEY,
            pc_compact TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            eastings INTEGER,
            northings INTEGER,
            incode TEXT,
            outcode TEXT,
            country TEXT,
            district TEXT,
            county TEXT,
            ward TEXT,
            parish TEXT,
            constituency TEXT,
            region TEXT,
            healthcare_region TEXT,
            nhs_health_authority TEXT,
            primary_care_trust TEXT,
            lower_output_area TEXT,
            middle_output_area TEXT,
            statistical_region TEXT,
            police_force TEXT,
            county_division TEXT,
            coordinate_quality INTEGER,
            date_introduced TEXT
        )''')
        
        # Create metadata table
        conn.execute('''
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        
        # Create indexes for fast lookups
        indexes = [
            'CREATE INDEX idx_pc_compact ON postcodes(pc_compact)',
            'CREATE INDEX idx_outcode ON postcodes(outcode)',
            'CREATE INDEX idx_incode ON postcodes(incode)', 
            'CREATE INDEX idx_location ON postcodes(latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL',
            'CREATE INDEX idx_country ON postcodes(country)',
            'CREATE INDEX idx_district ON postcodes(district)',
            'CREATE INDEX idx_constituency ON postcodes(constituency)',
            'CREATE INDEX idx_eastings_northings ON postcodes(eastings, northings) WHERE eastings IS NOT NULL AND northings IS NOT NULL'
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
        
        conn.commit()
        logger.info("Database schema created successfully")
        return conn
    
    def _clean_value(self, value):
        """Clean pandas values and convert to proper Python types"""
        if pd.isna(value) or value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if value.lower() in ('nan', '', 'null'):
                return None
            return value
        if isinstance(value, dict):
            # Handle remaining dict values by extracting name
            if 'name' in value:
                return value['name']
            elif 'value' in value:
                return value['value']
            else:
                # Convert dict to string as fallback
                return str(value)
        # Handle numpy types
        if hasattr(value, 'item'):
            return value.item()
        return value
    
    def _process_chunk_for_db(self, chunk: pd.DataFrame, csv_path: str = None) -> List[tuple]:
        """Process chunk and return list of tuples for database insertion"""
        # Get dynamic column mapping if CSV path provided
        if csv_path:
            csv_column_mapping = self.processor._get_csv_column_mapping(csv_path)
            processed_chunk = self.processor._process_chunk(chunk, csv_column_mapping)
        else:
            processed_chunk = self.processor._process_chunk(chunk)
        
        if processed_chunk.empty:
            return []
        
        # Convert to list of tuples with proper null handling
        rows = []
        for _, row in processed_chunk.iterrows():
            # Clean all values to handle pandas nan properly
            cleaned_row = {}
            for col in processed_chunk.columns:
                cleaned_row[col] = self._clean_value(row[col])
            
            # Create tuple in the order expected by SQL INSERT (streamlined schema)
            row_tuple = (
                cleaned_row.get('postcode'),
                cleaned_row.get('pc_compact'),
                cleaned_row.get('latitude'),
                cleaned_row.get('longitude'),
                cleaned_row.get('eastings'),
                cleaned_row.get('northings'),
                cleaned_row.get('incode'),
                cleaned_row.get('outcode'),
                cleaned_row.get('country'),
                cleaned_row.get('district'),
                cleaned_row.get('county'),
                cleaned_row.get('ward'),
                cleaned_row.get('parish'),
                cleaned_row.get('constituency'),
                cleaned_row.get('region'),
                cleaned_row.get('healthcare_region'),
                cleaned_row.get('nhs_health_authority'),
                cleaned_row.get('primary_care_trust'),
                cleaned_row.get('lower_output_area'),
                cleaned_row.get('middle_output_area'),
                cleaned_row.get('statistical_region'),
                cleaned_row.get('police_force'),
                cleaned_row.get('county_division'),
                cleaned_row.get('coordinate_quality'),
                cleaned_row.get('date_introduced'),
            )
            
            # Only add rows with valid postcodes
            if row_tuple[0]:  # postcode is not None/empty
                rows.append(row_tuple)
        
        return rows
    
    def create_database_from_csv_directory(self, csv_directory: str, db_path: str = "enhanced_postcodes.db"):
        """Create SQLite database from ONSPD CSV directory"""
        logger.info(f"Creating SQLite database: {db_path}")
        
        # Remove existing database
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info("Removed existing database")
        
        # Create database schema
        conn = self.create_database_schema(db_path)
        
        # Get CSV files
        csv_dir = Path(csv_directory)
        csv_files = list(csv_dir.glob("*.csv"))
        if not csv_files:
            raise ValueError(f"No CSV files found in {csv_directory}")
        
        logger.info(f"Found {len(csv_files)} CSV files to process")
        
        # Prepare SQL insert statement (25 columns for streamlined schema)
        insert_sql = '''
        INSERT OR REPLACE INTO postcodes VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )'''
        
        total_inserted = 0
        start_time = time.time()
        
        try:
            # Process files in batches
            for i, csv_file in enumerate(csv_files, 1):
                logger.info(f"Processing file {i}/{len(csv_files)}: {csv_file.name}")
                
                file_inserted = 0
                
                # Process CSV in chunks to manage memory
                for chunk in pd.read_csv(str(csv_file), chunksize=10000, header=0, 
                                       dtype=str, na_values=[''], keep_default_na=False,
                                       encoding='utf-8', low_memory=False):
                    
                    # Process chunk and get rows for insertion (pass CSV path for dynamic mapping)
                    rows_to_insert = self._process_chunk_for_db(chunk, str(csv_file))
                    
                    if rows_to_insert:
                        # Insert in batches for better performance
                        conn.executemany(insert_sql, rows_to_insert)
                        file_inserted += len(rows_to_insert)
                        total_inserted += len(rows_to_insert)
                
                logger.info(f"  Inserted {file_inserted:,} postcodes from {csv_file.name}")
                
                # Commit every few files to avoid huge transactions
                if i % 10 == 0:
                    conn.commit()
                    logger.info(f"  Committed transaction (total: {total_inserted:,})")
            
            # Final commit
            conn.commit()
            
            processing_time = time.time() - start_time
            
            # Add metadata
            metadata = [
                ('total_postcodes', str(total_inserted)),
                ('processing_time_seconds', str(int(processing_time))),
                ('processing_speed_per_second', str(int(total_inserted / processing_time))),
                ('source_date', 'February 2024'),
                ('created_timestamp', str(int(time.time()))),
                ('version', '1.0'),
                ('based_on', 'postcodes.io extraction logic (MIT License)')
            ]
            
            conn.executemany('INSERT INTO metadata VALUES (?, ?)', metadata)
            conn.commit()
            
            logger.info("Database creation complete!")
            logger.info(f"  Total postcodes: {total_inserted:,}")
            logger.info(f"  Processing time: {processing_time:.1f} seconds")
            logger.info(f"  Processing speed: {total_inserted/processing_time:,.0f} postcodes/second")
            
            # Get database size
            db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            logger.info(f"  Database size: {db_size_mb:.1f} MB")
            
            return db_path
            
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def validate_database(self, db_path: str):
        """Validate the created database"""
        logger.info("Validating database...")
        
        conn = sqlite3.connect(db_path)
        
        try:
            # Check total count
            total_count = conn.execute('SELECT COUNT(*) FROM postcodes').fetchone()[0]
            logger.info(f"Total postcodes in database: {total_count:,}")
            
            # Check for nulls in key fields
            null_postcodes = conn.execute('SELECT COUNT(*) FROM postcodes WHERE postcode IS NULL').fetchone()[0]
            if null_postcodes > 0:
                logger.warning(f"Found {null_postcodes} records with null postcodes")
            
            # Check coordinate coverage
            with_coords = conn.execute('SELECT COUNT(*) FROM postcodes WHERE latitude IS NOT NULL AND longitude IS NOT NULL').fetchone()[0]
            coord_rate = with_coords / total_count * 100
            logger.info(f"Coordinate coverage: {coord_rate:.1f}% ({with_coords:,}/{total_count:,})")
            
            # Check lookup resolution
            with_country = conn.execute('SELECT COUNT(*) FROM postcodes WHERE country IS NOT NULL').fetchone()[0]
            country_rate = with_country / total_count * 100
            logger.info(f"Country resolution: {country_rate:.1f}% ({with_country:,}/{total_count:,})")
            
            with_district = conn.execute('SELECT COUNT(*) FROM postcodes WHERE district IS NOT NULL').fetchone()[0]
            district_rate = with_district / total_count * 100
            logger.info(f"District resolution: {district_rate:.1f}% ({with_district:,}/{total_count:,})")
            
            # Test sample lookups
            sample = conn.execute('SELECT postcode, country, district, latitude, longitude FROM postcodes WHERE latitude IS NOT NULL LIMIT 3').fetchall()
            logger.info("Sample postcodes:")
            for postcode, country, district, lat, lon in sample:
                logger.info(f"  {postcode}: {country}, {district} ({lat}, {lon})")
            
            # Check indexes
            indexes = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'").fetchall()
            logger.info(f"Created {len(indexes)} indexes: {[idx[0] for idx in indexes]}")
            
            logger.info("✅ Database validation complete!")
            
        finally:
            conn.close()
    
    def test_query_performance(self, db_path: str):
        """Test query performance"""
        logger.info("Testing query performance...")
        
        conn = sqlite3.connect(db_path)
        
        try:
            # Test single postcode lookup
            start = time.time()
            result = conn.execute('SELECT * FROM postcodes WHERE postcode = ?', ('SW1A 1AA',)).fetchone()
            single_lookup_time = time.time() - start
            logger.info(f"Single lookup time: {single_lookup_time*1000:.2f}ms")
            
            # Test outcode lookup
            start = time.time()
            results = conn.execute('SELECT COUNT(*) FROM postcodes WHERE outcode = ?', ('SW1A',)).fetchone()
            outcode_lookup_time = time.time() - start
            logger.info(f"Outcode lookup time: {outcode_lookup_time*1000:.2f}ms (found {results[0]} postcodes)")
            
            # Test spatial query (if coordinates available)
            start = time.time()
            results = conn.execute('''
                SELECT postcode, 
                       (6371 * acos(cos(radians(51.5)) * cos(radians(latitude)) * 
                       cos(radians(longitude) - radians(-0.1)) + 
                       sin(radians(51.5)) * sin(radians(latitude)))) AS distance
                FROM postcodes 
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                  AND latitude BETWEEN 51.4 AND 51.6
                  AND longitude BETWEEN -0.2 AND 0.0
                ORDER BY distance LIMIT 10
            ''').fetchall()
            spatial_query_time = time.time() - start
            logger.info(f"Spatial query time: {spatial_query_time*1000:.2f}ms (found {len(results)} nearby postcodes)")
            
        finally:
            conn.close()

    @staticmethod
    def generate_outcode_python_files(db_path: str, output_dir: str):
        """Generate Python files for each outcode containing sets of incodes
        
        Args:
            db_path: Path to the SQLite database
            output_dir: Directory to create outcode files in
        """
        logger.info("Generating outcode-based Python files...")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create outcodes subdirectory
        outcodes_dir = output_path / "outcodes"
        outcodes_dir.mkdir(exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        
        try:
            # Get all unique outcodes
            outcodes = conn.execute('SELECT DISTINCT outcode FROM postcodes ORDER BY outcode').fetchall()
            logger.info(f"Found {len(outcodes)} unique outcodes")
            
            total_postcodes = 0
            
            # Create __init__.py for outcodes package
            init_content = '''"""
Outcode-based postcode validation files.
Each file contains incodes for a specific outcode.
"""

import os
from pathlib import Path
from typing import Set, Optional

def get_outcode_incodes(outcode: str) -> Optional[Set[str]]:
    """Get set of incodes for a given outcode"""
    try:
        module_name = f"outcodes.{outcode.lower()}"
        module = __import__(module_name, fromlist=[outcode.lower()])
        return getattr(module, 'INCODES', set())
    except (ImportError, AttributeError):
        return None

def is_postcode_valid(outcode: str, incode: str) -> bool:
    """Check if a postcode (outcode + incode) is valid"""
    incodes = get_outcode_incodes(outcode)
    return incodes is not None and incode in incodes
'''
            
            with open(outcodes_dir / "__init__.py", "w") as f:
                f.write(init_content)
            
            # Generate file for each outcode
            for (outcode,) in outcodes:
                if not outcode:  # Skip empty outcodes
                    continue
                    
                # Get all incodes for this outcode
                incodes = conn.execute(
                    'SELECT DISTINCT incode FROM postcodes WHERE outcode = ? ORDER BY incode',
                    (outcode,)
                ).fetchall()
                
                incode_set = {incode for (incode,) in incodes if incode}
                postcode_count = len(incode_set)
                total_postcodes += postcode_count
                
                # Create Python file for this outcode
                # Use lowercase for filename to avoid case issues
                filename = f"{outcode.lower()}.py"
                
                file_content = f'''"""
Postcodes for outcode {outcode}
Generated from ONS Postcode Directory
Contains {postcode_count} postcodes
"""

INCODES = {repr(incode_set)}
'''
                
                with open(outcodes_dir / filename, "w") as f:
                    f.write(file_content)
                
                logger.debug(f"Created {filename} with {postcode_count} incodes")
            
            # Create index file listing all outcodes
            outcode_list = [outcode for (outcode,) in outcodes if outcode]
            
            index_content = f'''"""
Index of all available outcodes.
Generated from ONS Postcode Directory
Total outcodes: {len(outcode_list)}
Total postcodes: {total_postcodes}
"""

AVAILABLE_OUTCODES = {repr(sorted(outcode_list))}

def get_all_outcodes():
    """Get list of all available outcodes"""
    return AVAILABLE_OUTCODES.copy()

def has_outcode(outcode: str) -> bool:
    """Check if an outcode is available"""
    return outcode.upper() in AVAILABLE_OUTCODES
'''
            
            with open(outcodes_dir / "index.py", "w") as f:
                f.write(index_content)
            
            logger.info(f"Generated {len(outcode_list)} outcode files")
            logger.info(f"Total postcodes: {total_postcodes:,}")
            
            # Calculate size savings
            original_size = len(f"POSTCODE_SET = {set()}")  # Rough estimate
            total_files_size = sum(
                os.path.getsize(outcodes_dir / f"{outcode.lower()}.py") 
                for outcode in outcode_list
            )
            
            logger.info(f"Generated files total size: {total_files_size / 1024 / 1024:.1f} MB")
            logger.info(f"Average file size: {total_files_size / len(outcode_list) / 1024:.1f} KB")
            
            return outcodes_dir
            
        finally:
            conn.close()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Create SQLite database from ONSPD data')
    parser.add_argument('onspd_directory', nargs='?', help='Path to ONSPD multi_csv directory (optional if only generating outcodes)')
    parser.add_argument('--output', default='enhanced_postcodes.db', help='Output database path')
    parser.add_argument('--data-dir', default='../data', help='Data directory path')
    parser.add_argument('--validate', action='store_true', help='Validate database after creation')
    parser.add_argument('--test-performance', action='store_true', help='Test query performance')
    parser.add_argument('--generate-outcodes', help='Generate outcode Python files to specified directory')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Handle case where we only want to generate outcodes from existing database
        if args.generate_outcodes and not args.onspd_directory:
            # Use existing database for outcode generation only
            if not os.path.exists(args.output):
                raise FileNotFoundError(f"Database not found: {args.output}")
            
            print(f"Generating outcode files from existing database: {args.output}")
            outcodes_dir = PostcodeSQLiteCreator.generate_outcode_python_files(args.output, args.generate_outcodes)
            print(f"✅ Outcode files generated successfully: {outcodes_dir}")
            return 0
        
        # Require ONSPD directory for database creation
        if not args.onspd_directory:
            parser.error("onspd_directory is required unless using --generate-outcodes with existing database")
        
        creator = PostcodeSQLiteCreator(data_dir=args.data_dir)
        
        # Create database
        db_path = creator.create_database_from_csv_directory(
            args.onspd_directory,
            args.output
        )
        
        # Validate if requested
        if args.validate:
            creator.validate_database(db_path)
        
        # Test performance if requested
        if args.test_performance:
            creator.test_query_performance(db_path)
        
        # Generate outcode files if requested
        if args.generate_outcodes:
            outcodes_dir = PostcodeSQLiteCreator.generate_outcode_python_files(db_path, args.generate_outcodes)
            print(f"✅ Outcode files generated successfully: {outcodes_dir}")
        
        print(f"✅ SQLite database created successfully: {db_path}")
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())