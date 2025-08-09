#!/usr/bin/env python3
"""
Enhanced ONS Postcode Directory processor
Based on postcodes.io extraction logic (MIT License)
"""

import pandas as pd
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging
import time
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ProcessingStats:
    """Statistics for processing operations"""
    total_rows_processed: int = 0
    active_postcodes: int = 0
    terminated_postcodes: int = 0
    with_coordinates: int = 0
    processing_time: float = 0.0
    
class ONSPDProcessor:
    """
    Enhanced ONS Postcode Directory processor based on postcodes.io logic
    """
    
    # Port from postcodes.io postcode.ts:841-886 with corrections for ONSPD Feb 2024
    ONSPD_FIELD_MAPPINGS = [
        {"column": "postcode", "onspd_code": "pcds"},
        {"column": "pc_compact", "onspd_code": "pcds", "transform": lambda x: x.replace(" ", "") if x else ""},
        {"column": "eastings", "onspd_code": "oseast1m", "type": "int"},
        {"column": "northings", "onspd_code": "osnrth1m", "type": "int"},
        # Fixed coordinate mapping - latitude depends on northings, longitude depends on eastings
        {"column": "latitude", "onspd_code": "lat", "type": "float", "depends_on": "osnrth1m"},
        {"column": "longitude", "onspd_code": "long", "type": "float", "depends_on": "oseast1m"},
        {"column": "country_code", "onspd_code": "ctry"},
        {"column": "nhs_ha_code", "onspd_code": "oshlthau"},
        {"column": "admin_county_id", "onspd_code": "oscty"},
        {"column": "admin_district_id", "onspd_code": "oslaua"},
        {"column": "admin_ward_id", "onspd_code": "osward"},
        {"column": "parish_id", "onspd_code": "parish"},
        {"column": "quality", "onspd_code": "osgrdind", "type": "int"},
        {"column": "constituency_id", "onspd_code": "pcon"},
        {"column": "european_electoral_region_code", "onspd_code": "eer"},
        {"column": "region_code", "onspd_code": "rgn"},
        {"column": "primary_care_trust_code", "onspd_code": "pct"},
        {"column": "lsoa_id", "onspd_code": "lsoa11"},
        {"column": "msoa_id", "onspd_code": "msoa11"},
        # Updated for ONSPD Feb 2024: ITL replaces NUTS
        {"column": "nuts_id", "onspd_code": "itl"},
        {"column": "incode", "onspd_code": "pcds", "transform": lambda x: x.split(" ")[1] if x and " " in x else ""},
        {"column": "outcode", "onspd_code": "pcds", "transform": lambda x: x.split(" ")[0] if x and " " in x else ""},
        {"column": "ced_id", "onspd_code": "ced"},
        # Updated for ONSPD Feb 2024: SICBL replaces CCG
        {"column": "ccg_id", "onspd_code": "sicbl"},
        {"column": "date_of_introduction", "onspd_code": "dointr"},
        {"column": "date_of_termination", "onspd_code": "doterm"},
        {"column": "pfa_id", "onspd_code": "pfa"},
    ]
    
    def __init__(self, data_dir: str = "../data"):
        self.data_dir = Path(data_dir)
        self.lookup_tables = self._load_lookup_tables()
        self.column_mapping = self._load_onspd_schema()
        logger.info(f"Initialized processor with {len(self.lookup_tables)} lookup tables")
        
    def _load_lookup_tables(self) -> Dict[str, Dict]:
        """Load all JSON lookup tables from postcodes.io"""
        tables = {}
        lookup_files = [
            "countries.json", "districts.json", "constituencies.json",
            "counties.json", "wards.json", "nhsHa.json", "regions.json",
            "european_registers.json", "pcts.json", "ccgs.json",
            "lsoa.json", "msoa.json", "nuts.json", "parishes.json",
            "police_force_areas.json", "ceds.json"
        ]
        
        for file in lookup_files:
            file_path = self.data_dir / "lookup_tables" / file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        tables[file.replace('.json', '')] = json.load(f)
                    logger.info(f"Loaded lookup table: {file}")
                except Exception as e:
                    logger.warning(f"Failed to load {file}: {e}")
            else:
                logger.warning(f"Lookup table not found: {file}")
        
        return tables
    
    def _load_onspd_schema(self) -> Dict[str, int]:
        """Load ONSPD schema and create column index mapping"""
        schema_path = self.data_dir / "schemas" / "onspd_schema.json"
        if not schema_path.exists():
            raise FileNotFoundError(f"ONSPD schema not found at {schema_path}")
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        # Create column index mapping
        col_mapping = {item['code']: i for i, item in enumerate(schema)}
        logger.info(f"Loaded ONSPD schema with {len(col_mapping)} columns")
        return col_mapping
    
    def _get_csv_column_mapping(self, csv_path: str) -> Dict[str, int]:
        """Get actual column mapping from CSV headers"""
        # Read just the header row to get actual column names
        df_header = pd.read_csv(csv_path, nrows=0)
        column_names = [col.lower() for col in df_header.columns]
        
        # Create mapping from column names to indices
        mapping = {col: i for i, col in enumerate(column_names)}
        
        logger.debug(f"CSV columns found: {list(mapping.keys())}")
        return mapping
    
    def process_onspd_csv_directory(self, csv_directory: str, chunk_size: int = 50000) -> pd.DataFrame:
        """
        Process all CSV files in a directory (e.g., multi_csv from ONSPD)
        """
        csv_dir = Path(csv_directory)
        if not csv_dir.exists():
            raise FileNotFoundError(f"CSV directory not found: {csv_directory}")
        
        # Find all CSV files
        csv_files = list(csv_dir.glob("*.csv"))
        if not csv_files:
            raise ValueError(f"No CSV files found in {csv_directory}")
        
        logger.info(f"Found {len(csv_files)} CSV files to process")
        
        all_chunks = []
        stats = ProcessingStats()
        start_time = time.time()
        
        for i, csv_file in enumerate(csv_files, 1):
            logger.info(f"Processing file {i}/{len(csv_files)}: {csv_file.name}")
            file_stats = self.process_onspd_csv(str(csv_file), chunk_size=chunk_size)
            
            if len(file_stats) > 0:
                all_chunks.append(file_stats)
                stats.total_rows_processed += len(file_stats)
                stats.active_postcodes += len(file_stats[file_stats['date_of_termination'].isna()])
                stats.with_coordinates += len(file_stats.dropna(subset=['latitude', 'longitude']))
        
        if not all_chunks:
            logger.warning("No data processed from any CSV files")
            return pd.DataFrame()
        
        logger.info("Combining all processed data...")
        combined_df = pd.concat(all_chunks, ignore_index=True)
        
        stats.processing_time = time.time() - start_time
        stats.terminated_postcodes = stats.total_rows_processed - stats.active_postcodes
        
        logger.info(f"Processing complete!")
        logger.info(f"  Total postcodes processed: {stats.total_rows_processed:,}")
        logger.info(f"  Active postcodes: {stats.active_postcodes:,}")
        logger.info(f"  Terminated postcodes: {stats.terminated_postcodes:,}")
        logger.info(f"  With coordinates: {stats.with_coordinates:,} ({stats.with_coordinates/stats.total_rows_processed*100:.1f}%)")
        logger.info(f"  Processing time: {stats.processing_time:.1f} seconds")
        logger.info(f"  Processing speed: {stats.total_rows_processed/stats.processing_time:,.0f} postcodes/second")
        
        return combined_df
    
    def process_onspd_csv(self, csv_path: str, chunk_size: int = 50000) -> pd.DataFrame:
        """
        Process ONSPD CSV file using postcodes.io logic with chunked processing
        """
        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        logger.debug(f"Processing CSV: {csv_file.name}")
        
        # Get dynamic column mapping from actual CSV headers
        csv_column_mapping = self._get_csv_column_mapping(csv_path)
        
        # Process CSV in chunks for memory efficiency
        chunks = []
        chunk_count = 0
        
        try:
            for chunk in pd.read_csv(csv_path, chunksize=chunk_size, header=0, 
                                   dtype=str, na_values=[''], keep_default_na=False,
                                   encoding='utf-8', low_memory=False):
                chunk_count += 1
                processed_chunk = self._process_chunk(chunk, csv_column_mapping)
                if not processed_chunk.empty:
                    chunks.append(processed_chunk)
                
                if chunk_count % 10 == 0:
                    logger.debug(f"  Processed {chunk_count} chunks from {csv_file.name}")
        
        except Exception as e:
            logger.error(f"Error processing {csv_file.name}: {e}")
            return pd.DataFrame()
        
        if not chunks:
            logger.warning(f"No valid data found in {csv_file.name}")
            return pd.DataFrame()
        
        result = pd.concat(chunks, ignore_index=True)
        logger.debug(f"  Extracted {len(result):,} postcodes from {csv_file.name}")
        return result
    
    def _process_chunk(self, chunk: pd.DataFrame, csv_column_mapping: Dict[str, int] = None) -> pd.DataFrame:
        """Process a chunk of ONSPD data using dynamic column mapping"""
        if csv_column_mapping is None:
            csv_column_mapping = self.column_mapping
        
        processed_rows = []
        
        for _, row in chunk.iterrows():
            # Skip terminated postcodes (same logic as postcodes.io)
            doterm_idx = csv_column_mapping.get('doterm', -1)
            if doterm_idx >= 0 and doterm_idx < len(row):
                doterm_val = str(row.iloc[doterm_idx]).strip()
                if doterm_val and doterm_val != 'nan' and len(doterm_val) > 0:
                    continue
                
            # Skip header rows
            pcd_idx = csv_column_mapping.get('pcd', -1)
            if pcd_idx >= 0 and pcd_idx < len(row):
                if str(row.iloc[pcd_idx]).strip().lower() == 'pcd':
                    continue
            
            processed_row = {}
            
            # Extract fields using postcodes.io mapping
            for field_def in self.ONSPD_FIELD_MAPPINGS:
                onspd_idx = csv_column_mapping.get(field_def['onspd_code'], -1)
                if onspd_idx >= 0 and onspd_idx < len(row):
                    value = str(row.iloc[onspd_idx]).strip()
                    
                    # Handle empty values
                    if not value or value.lower() == 'nan':
                        value = None
                    
                    # Check dependencies (postcodes.io logic: coordinates depend on eastings/northings)
                    if 'depends_on' in field_def:
                        depends_idx = csv_column_mapping.get(field_def['depends_on'], -1)
                        if depends_idx >= 0 and depends_idx < len(row):
                            depends_val = str(row.iloc[depends_idx]).strip()
                            # Per postcodes.io line 852-860: coordinates are null if eastings/northings are empty
                            if not depends_val or depends_val.lower() == 'nan' or depends_val == '' or depends_val == '0':
                                value = None
                    
                    # Apply transformations
                    if 'transform' in field_def and value:
                        try:
                            value = field_def['transform'](value)
                        except Exception as e:
                            logger.debug(f"Transform failed for {field_def['column']}: {e}")
                            value = None
                    
                    # Type conversion
                    if value and field_def.get('type'):
                        try:
                            if field_def['type'] == 'int':
                                value = int(float(value))
                            elif field_def['type'] == 'float':
                                value = float(value)
                        except (ValueError, TypeError):
                            value = None
                    
                    processed_row[field_def['column']] = value
                else:
                    processed_row[field_def['column']] = None
            
            # Add human-readable names using lookup tables
            self._add_human_readable_names(processed_row)
            
            # Only add row if we have a valid postcode
            if processed_row.get('postcode'):
                processed_rows.append(processed_row)
        
        return pd.DataFrame(processed_rows)
    
    def _add_human_readable_names(self, row: Dict):
        """Add human-readable names using lookup tables"""
        mappings = [
            ('country_code', 'countries', 'country'),
            ('admin_district_id', 'districts', 'admin_district'),
            ('admin_county_id', 'counties', 'admin_county'),
            ('admin_ward_id', 'wards', 'admin_ward'),
            ('parish_id', 'parishes', 'parish'),
            ('constituency_id', 'constituencies', 'parliamentary_constituency'),
            ('region_code', 'regions', 'region'),
            ('european_electoral_region_code', 'european_registers', 'european_electoral_region'),
            ('primary_care_trust_code', 'pcts', 'primary_care_trust'),
            # Updated for ONSPD Feb 2024: ccg_id now contains SICBL data
            ('ccg_id', 'ccgs', 'ccg'),
            ('lsoa_id', 'lsoa', 'lsoa'),
            ('msoa_id', 'msoa', 'msoa'),
            # Updated for ONSPD Feb 2024: nuts_id now contains ITL data, but we keep nuts lookup table
            ('nuts_id', 'nuts', 'nuts'),
            ('pfa_id', 'police_force_areas', 'pfa'),
            ('ced_id', 'ceds', 'ced'),
            ('nhs_ha_code', 'nhsHa', 'nhs_ha'),
        ]
        
        for code_field, table_name, name_field in mappings:
            code = row.get(code_field)
            if code and table_name in self.lookup_tables:
                lookup_table = self.lookup_tables[table_name]
                
                if isinstance(lookup_table, dict) and code in lookup_table:
                    lookup_result = lookup_table[code]
                    
                    # Handle different lookup table formats
                    if isinstance(lookup_result, dict):
                        # For CCG, NUTS etc. that have nested structure
                        if 'name' in lookup_result:
                            row[name_field] = lookup_result['name']
                        elif 'value' in lookup_result:
                            row[name_field] = lookup_result['value']
                        else:
                            # Fallback: take the whole dict (will be handled by clean_value)
                            row[name_field] = lookup_result
                    else:
                        # Simple string lookup
                        row[name_field] = lookup_result
                        
                elif isinstance(lookup_table, list):
                    # Array-based lookup (find by code field)
                    match = next((item for item in lookup_table if item.get('code') == code), None)
                    if match:
                        if isinstance(match, dict):
                            row[name_field] = match.get('name', match.get('value'))
                        else:
                            row[name_field] = match

    def generate_enhanced_postcode_data(self, onspd_csv_directory: str, 
                                      output_path: str = None) -> str:
        """Generate enhanced postcode dataset"""
        logger.info("Starting enhanced postcode dataset generation...")
        
        # Process all ONSPD data
        df = self.process_onspd_csv_directory(onspd_csv_directory)
        
        if df.empty:
            raise ValueError("No data processed from ONSPD files")
        
        # Filter active postcodes only
        logger.info("Filtering active postcodes...")
        active_df = df[df['date_of_termination'].isna() | (df['date_of_termination'] == '')]
        logger.info(f"Active postcodes: {len(active_df):,} out of {len(df):,}")
        
        # Create the enhanced dataset
        logger.info("Creating enhanced dataset structure...")
        enhanced_data = {}
        
        for _, row in active_df.iterrows():
            postcode = row['postcode']
            if not postcode:
                continue
                
            enhanced_data[postcode] = {
                'coordinates': {
                    'latitude': row.get('latitude'),
                    'longitude': row.get('longitude'),
                    'eastings': row.get('eastings'),
                    'northings': row.get('northings'),
                },
                'administrative': {
                    'country': row.get('country'),
                    'admin_district': row.get('admin_district'),
                    'admin_county': row.get('admin_county'),
                    'admin_ward': row.get('admin_ward'),
                    'parish': row.get('parish'),
                    'constituency': row.get('parliamentary_constituency'),
                    'region': row.get('region'),
                    'european_electoral_region': row.get('european_electoral_region'),
                },
                'healthcare': {
                    'ccg': row.get('ccg'),
                    'primary_care_trust': row.get('primary_care_trust'),
                    'nhs_ha': row.get('nhs_ha'),
                },
                'statistical': {
                    'lsoa': row.get('lsoa'),
                    'msoa': row.get('msoa'),
                    'nuts': row.get('nuts'),
                },
                'codes': {
                    'country_code': row.get('country_code'),
                    'admin_district_id': row.get('admin_district_id'),
                    'admin_county_id': row.get('admin_county_id'),
                    'admin_ward_id': row.get('admin_ward_id'),
                    'parish_id': row.get('parish_id'),
                    'constituency_id': row.get('constituency_id'),
                    'ccg_id': row.get('ccg_id'),
                    'lsoa_id': row.get('lsoa_id'),
                    'msoa_id': row.get('msoa_id'),
                    'nuts_id': row.get('nuts_id'),
                    'pfa_id': row.get('pfa_id'),
                    'ced_id': row.get('ced_id'),
                },
                'quality': row.get('quality', 1),
                'date_introduced': row.get('date_of_introduction'),
                'incode': row.get('incode'),
                'outcode': row.get('outcode'),
            }
        
        # Output format
        if output_path:
            output_file = output_path
        else:
            # Use current date
            import datetime
            date_str = datetime.datetime.now().strftime('%Y_%m')
            output_file = f"enhanced_postcodes_{date_str}.py"
        
        logger.info(f"Writing enhanced dataset to {output_file}...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Enhanced UK Postcodes Dataset\n")
            f.write(f"# Generated on {pd.Timestamp.now()}\n")
            f.write(f"# Based on postcodes.io extraction logic (MIT License)\n")
            f.write(f"# Total active postcodes: {len(enhanced_data):,}\n")
            f.write(f"# Source: ONS Postcode Directory\n\n")
            f.write("ENHANCED_POSTCODE_DATA = ")
            
            # Write the data in a more readable format
            import pprint
            formatted_data = pprint.pformat(enhanced_data, width=120, indent=4)
            f.write(formatted_data)
            f.write("\n")
        
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        logger.info(f"Enhanced dataset generated successfully!")
        logger.info(f"  Output file: {output_file}")
        logger.info(f"  File size: {file_size_mb:.1f} MB")
        logger.info(f"  Postcodes: {len(enhanced_data):,}")
        
        return output_file

def main():
    """Main entry point for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced ONSPD processor based on postcodes.io')
    parser.add_argument('onspd_directory', help='Path to ONSPD multi_csv directory')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--data-dir', default='../data', help='Data directory path')
    parser.add_argument('--chunk-size', type=int, default=50000, help='Chunk size for CSV processing')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        processor = ONSPDProcessor(data_dir=args.data_dir)
        output_file = processor.generate_enhanced_postcode_data(
            args.onspd_directory, 
            args.output
        )
        
        print(f"✅ Enhanced postcode data generated: {output_file}")
        
    except Exception as e:
        logger.error(f"Failed to process ONSPD data: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())