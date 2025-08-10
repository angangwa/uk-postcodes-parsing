# UK Postcode Data Processing Pipeline - Technical Guide

## Overview

This guide explains how the UK postcode data processing pipeline works. The library provides **two complementary approaches**:

1. **Production Usage**: Downloads pre-built database (797MB) from GitHub releases
2. **Development/Custom Builds**: Build tools in `onspd_tools/` to regenerate database from raw ONSPD data

This guide covers both approaches, assumptions made, processing steps, and validation methods.

## Data Source & Distribution

### Production Database (Recommended)
- **Source**: Pre-built SQLite database hosted on GitHub releases
- **Size**: 797MB download
- **Schema**: 25 streamlined columns (human-readable names, no GSS codes)
- **Coverage**: 1,799,395 active postcodes (Feb 2025)
- **Usage**: Automatic download via `uk_postcodes_parsing` library

### Build-from-Source (Advanced)
- **Source**: ONS Postcode Directory (ONSPD) February 2024 UK dataset  
- **Format**: CSV files split by postcode area (124 files, ~1.8M postcodes total)
- **Schema**: Full 53-column ONSPD specification with GSS codes
- **Usage**: Manual build using `onspd_tools/` (developers only)

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
-- Streamlined schema with 25 essential columns (GSS codes removed)
CREATE TABLE postcodes (
    postcode TEXT PRIMARY KEY,
    pc_compact TEXT NOT NULL,
    latitude REAL, longitude REAL,
    eastings INTEGER, northings INTEGER,
    incode TEXT, outcode TEXT,
    -- Administrative fields (country, district, county, ward, parish)
    -- Healthcare fields (healthcare_region, nhs_health_authority, primary_care_trust)  
    -- Statistical fields (lower_output_area, middle_output_area, statistical_region)
    -- Service fields (police_force, county_division)
    -- Metadata (coordinate_quality, date_introduced)
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

### Administrative Hierarchy (Human-readable names only)
- `country`: England, Scotland, Wales, Northern Ireland
- `district`: Local authority district (e.g., "Westminster")
- `county`: Administrative county (if applicable)
- `ward`: Electoral ward (e.g., "St James's")
- `parish`: Civil parish (England/Wales only)
- `constituency`: Parliamentary constituency
- `region`: Government office region (e.g., "London")

### Healthcare Regions (Human-readable names only)
- `healthcare_region`: Sub ICB Location (e.g., "NHS North West London")
- `nhs_health_authority`: NHS Health Authority region (e.g., "London")
- `primary_care_trust`: Primary Care Trust (e.g., "Westminster")

### Statistical Areas (Human-readable names only)
- `lower_output_area`: Lower Super Output Area (2011 census)
- `middle_output_area`: Middle Super Output Area (2011 census)  
- `statistical_region`: International Territorial Level (formerly NUTS)

## Validation Methods

### 1. Coordinate Validation
```python
# Test that lat/lon are correctly populated
sample = conn.execute("""
    SELECT postcode, latitude, longitude, eastings, northings 
    FROM postcodes WHERE latitude IS NOT NULL LIMIT 5
""").fetchall()

# Verify coordinate pair consistency
broken_coords = conn.execute("""
    SELECT COUNT(*) FROM postcodes 
    WHERE latitude IS NULL AND longitude IS NOT NULL
       OR latitude IS NOT NULL AND longitude IS NULL
""").fetchone()[0]
assert broken_coords == 0  # Should be 0 (coordinates are paired)
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
# Verify lookup resolution works (streamlined schema has names only)
sample = conn.execute("""
    SELECT district, healthcare_region 
    FROM postcodes 
    WHERE district IS NOT NULL LIMIT 1
""").fetchone()

# Names should be populated (GSS codes available only in build tools)
assert sample[0] is not None  # District name
assert sample[1] is not None  # Healthcare region name
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

- **Processing Speed**: ~8,650 postcodes/second (when building from source)
- **Memory Usage**: 50MB chunks processed in memory
- **Database Size**: 797MB SQLite file (1.8M postcodes, streamlined 25-column schema)  
- **Lookup Performance**: <1ms single postcode queries
- **Spatial Queries**: <100ms nearest-neighbor searches
- **Download Speed**: ~30MB/s average (for pre-built database)

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