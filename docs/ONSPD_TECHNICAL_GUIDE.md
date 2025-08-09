# UK Postcode Data Processing Pipeline - Technical Guide

## Overview

This guide explains how the UK postcode data processing pipeline works, including the assumptions made, processing steps, and validation methods. It is designed for developers and data engineers who need to understand or validate the implementation.

## Data Source

The pipeline processes ONS Postcode Directory (ONSPD) data from the Office for National Statistics:

- **Source**: ONSPD February 2024 UK dataset
- **Format**: CSV files split by postcode area (124 files, ~1.8M postcodes total)
- **Specification**: Based on ONSPD User Guide Feb 2024 (53 columns per record)

## Processing Logic Foundation

The implementation is based on the [postcodes.io](https://postcodes.io) extraction logic (MIT License), specifically:

- Field mapping logic from `postcode.ts:841-886`
- Coordinate dependency validation from `postcode.ts:850-861` 
- GSS code lookup resolution using postcodes.io lookup tables
- Active postcode filtering (excludes terminated postcodes)

## Key Assumptions

### 1. Field Mapping Updates
- **CCG → SICBL**: Clinical Commissioning Groups replaced by Sub ICB Locations in Feb 2024
- **NUTS → ITL**: NUTS regions replaced by International Territorial Levels in Feb 2024
- **Dynamic Column Detection**: CSV headers are read dynamically rather than using static mappings

### 2. Coordinate Dependencies
Following postcodes.io logic:
- `latitude` is null if `northings` (osnrth1m) is empty/zero
- `longitude` is null if `eastings` (oseast1m) is empty/zero
- Coordinates are derived from Ordnance Survey grid references

### 3. Data Quality Expectations
- ~99.3% of postcodes have valid coordinates
- ~99.5% have healthcare region assignments (SICBL/CCG)
- ~93.9% have statistical region assignments (ITL/NUTS)
- ~99.9% have administrative district assignments

## Processing Steps

### 1. Initialization (`ONSPDProcessor.__init__`)
```python
# Load 16 lookup tables from postcodes.io data
# - countries.json, districts.json, constituencies.json, etc.
# Load ONSPD schema (53 column definitions)
# Initialize field mappings with dependency rules
```

### 2. Dynamic Column Mapping (`_get_csv_column_mapping`)
```python
# Read CSV headers to get actual column positions
# Map column names to indices (case-insensitive)
# Handle variations in ONSPD data structure
```

### 3. Chunk Processing (`_process_chunk`)
For each 10,000-row chunk:

1. **Filter Records**:
   - Skip terminated postcodes (`doterm` field not empty)
   - Skip header rows (`pcd` field = "pcd")

2. **Extract Fields**:
   - Map 25+ fields using postcodes.io field definitions
   - Apply coordinate dependency logic
   - Perform type conversions (int, float)
   - Execute field transformations (e.g., incode/outcode splitting)

3. **Resolve Lookups**:
   - Convert GSS codes to human-readable names
   - Handle nested dictionary structures in lookup tables
   - Maintain code→name relationships

### 4. Database Creation (`PostcodeSQLiteCreator`)
```sql
-- Schema with 42 optimized columns
CREATE TABLE postcodes (
    postcode TEXT PRIMARY KEY,
    pc_compact TEXT NOT NULL,
    latitude REAL, longitude REAL,
    eastings INTEGER, northings INTEGER,
    -- Administrative fields (country, district, county, ward, parish)
    -- Healthcare fields (ccg, nhs_ha, primary_care_trust)  
    -- Statistical fields (lsoa, msoa, nuts)
    -- Code fields (all _id suffixed fields)
    -- Metadata (quality, date_introduced, incode, outcode)
);

-- Performance indexes
CREATE INDEX idx_pc_compact ON postcodes(pc_compact);
CREATE INDEX idx_location ON postcodes(latitude, longitude);
CREATE INDEX idx_outcode ON postcodes(outcode);
-- + 5 additional indexes for fast lookups
```

## Field Mapping Details

### Core Fields (Always Present)
- `postcode`: Full postcode (e.g., "SW1A 1AA")  
- `pc_compact`: Postcode without spaces ("SW1A1AA")
- `incode`: Last part after space ("1AA")
- `outcode`: First part before space ("SW1A")

### Geographic Coordinates
- `latitude`/`longitude`: WGS84 decimal degrees (depends on OS grid refs)
- `eastings`/`northings`: Ordnance Survey grid references
- `quality`: Positional accuracy indicator (1-10 scale)

### Administrative Hierarchy
- `country`/`country_code`: England, Scotland, Wales, Northern Ireland
- `admin_district`/`admin_district_id`: Local authority district
- `admin_county`/`admin_county_id`: Administrative county (if applicable)
- `admin_ward`/`admin_ward_id`: Electoral ward
- `parish`/`parish_id`: Civil parish (England/Wales)

### Healthcare Regions
- `ccg`/`ccg_id`: Sub ICB Location (formerly Clinical Commissioning Group)
- `nhs_ha`/`nhs_ha_code`: NHS Health Authority region
- `primary_care_trust`/`primary_care_trust_code`: Primary Care Trust

### Statistical Areas
- `lsoa`/`lsoa_id`: Lower Super Output Area (2011 census)
- `msoa`/`msoa_id`: Middle Super Output Area (2011 census)  
- `nuts`/`nuts_id`: International Territorial Level (formerly NUTS)

## Validation Methods

### 1. Coordinate Validation
```python
# Test that lat/lon are correctly populated
sample = conn.execute("""
    SELECT postcode, latitude, longitude, eastings, northings 
    FROM postcodes WHERE latitude IS NOT NULL LIMIT 5
""").fetchall()

# Verify no longitude-without-latitude issues
broken_coords = conn.execute("""
    SELECT COUNT(*) FROM postcodes 
    WHERE latitude IS NULL AND longitude IS NOT NULL
""").fetchone()[0]
assert broken_coords == 0
```

### 2. Field Coverage Analysis
```python
# Check coverage percentages
stats = conn.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(latitude) as with_coords,
        COUNT(ccg) as with_ccg,
        COUNT(nuts) as with_nuts
    FROM postcodes
""").fetchone()

coord_coverage = with_coords / total * 100
# Expected: ~99.3% coordinate coverage
```

### 3. Lookup Resolution Testing
```python
# Verify GSS code → name resolution works
sample = conn.execute("""
    SELECT admin_district, admin_district_id 
    FROM postcodes 
    WHERE admin_district IS NOT NULL LIMIT 1
""").fetchone()

# Both name and ID should be populated
assert sample[0] is not None  # Human readable name
assert sample[1] is not None  # GSS code
```

## Error Handling

### Common Issues
1. **Missing Lookup Tables**: Processor logs warnings but continues
2. **Invalid Coordinates**: Set to NULL following dependency rules  
3. **Malformed Postcodes**: Skipped during processing
4. **Schema Changes**: Dynamic column mapping handles new/removed fields

### Recovery Strategies
- **Partial Processing**: Individual CSV files can be reprocessed
- **Incremental Updates**: Database supports INSERT OR REPLACE operations
- **Validation Rollback**: Keep original data archived for re-processing

## Performance Characteristics

- **Processing Speed**: ~8,650 postcodes/second
- **Memory Usage**: 50MB chunks processed in memory
- **Database Size**: ~958MB SQLite file (1.8M postcodes)  
- **Lookup Performance**: <1ms single postcode queries
- **Spatial Queries**: <100ms nearest-neighbor searches

## Dependencies

### External Libraries
- `pandas`: CSV processing and data manipulation
- `sqlite3`: Database storage and querying
- Standard library: `json`, `pathlib`, `logging`, `time`

### Data Dependencies
- 16 JSON lookup tables from postcodes.io
- ONSPD schema definition (53 columns)
- ONSPD CSV files (124 files by postcode area)

## Extensibility

### Adding New Fields
1. Update `ONSPD_FIELD_MAPPINGS` in `onspd_processor.py`
2. Add column to database schema in `postcode_database_builder.py`
3. Add lookup table if GSS code resolution needed
4. Update field coverage validation tests

### Supporting New ONSPD Versions
1. Download new lookup tables from postcodes.io
2. Update schema JSON file if column structure changes
3. Test field mapping validation with new data
4. Update documentation with any breaking changes

This technical guide provides the foundation for understanding, validating, and extending the UK postcode data processing pipeline.