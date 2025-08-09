# UK Postcode Data Processing Pipeline - Usage Guide

## Quick Start

Transform ONS Postcode Directory (ONSPD) data into a searchable SQLite database with comprehensive geographic and administrative metadata.

```bash
# 1. Process ONSPD CSV files and create database
cd onspd_tools
python postcode_database_builder.py /path/to/onspd/multi_csv --output postcodes.db --validate

# 2. Use the generated database
python -c "
import sqlite3
conn = sqlite3.connect('../postcodes.db')
result = conn.execute('SELECT * FROM postcodes WHERE postcode = ?', ('SW1A 1AA',)).fetchone()
print(result)
"
```

## Input Requirements

### ONSPD Data Structure
```
ONSPD_FEB_2024_UK/
├── Data/
│   ├── multi_csv/                    # Required: 124 CSV files
│   │   ├── ONSPD_FEB_2024_UK_AB.csv  # Aberdeen postcodes
│   │   ├── ONSPD_FEB_2024_UK_B.csv   # Birmingham postcodes  
│   │   └── ...                       # One file per postcode area
│   └── ONSPD_FEB_2024_UK.csv        # Optional: Combined file
└── User Guide/
    └── ONSPD User Guide Feb 2024.pdf # Reference documentation
```

### Lookup Tables
Required JSON files (included in `data/lookup_tables/`):
- `countries.json` - Country names and codes
- `districts.json` - Local authority districts
- `counties.json` - Administrative counties
- `constituencies.json` - Parliamentary constituencies
- `wards.json` - Electoral wards
- `parishes.json` - Civil parishes
- `ccgs.json` - Clinical commissioning groups
- `nuts.json` - Statistical regions
- `lsoa.json`, `msoa.json` - Census output areas
- `regions.json` - Government office regions
- `nhsHa.json` - NHS health authorities
- `pcts.json` - Primary care trusts
- `police_force_areas.json` - Police force boundaries
- `ceds.json` - County electoral divisions
- `european_registers.json` - European electoral regions

## Tools

### 1. ONSPD Processor (`onspd_processor.py`)

Processes raw ONSPD CSV files into structured pandas DataFrames.

```bash
python onspd_processor.py [OPTIONS] ONSPD_DIRECTORY

# Required:
#   ONSPD_DIRECTORY    Path to ONSPD multi_csv directory

# Options:
#   --output OUTPUT    Output file path (default: auto-generated)
#   --data-dir DIR     Data directory path (default: ../data)
#   --chunk-size SIZE  CSV chunk size (default: 50000)
#   --verbose          Enable debug logging
```

**Example:**
```bash
cd onspd_tools
python onspd_processor.py ../archive/ONSPD_FEB_2024_UK/Data/multi_csv \
  --output postcodes_processed.py \
  --verbose
```

### 2. Database Builder (`postcode_database_builder.py`)

Creates optimized SQLite database from ONSPD data.

```bash
python postcode_database_builder.py [OPTIONS] ONSPD_DIRECTORY

# Required:
#   ONSPD_DIRECTORY    Path to ONSPD multi_csv directory

# Options:
#   --output FILE      Database file path (default: postcodes.db)
#   --data-dir DIR     Data directory path (default: ../data)
#   --validate         Run validation after creation
#   --test-performance Test query performance
#   --verbose          Enable debug logging
```

**Example:**
```bash
cd onspd_tools
python postcode_database_builder.py ../archive/ONSPD_FEB_2024_UK/Data/multi_csv \
  --output ../postcodes.db \
  --validate \
  --test-performance
```

## Output Formats

### SQLite Database Schema

**Table: `postcodes`** (42 columns, 1.8M rows)

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `postcode` | TEXT PRIMARY KEY | Full postcode | "SW1A 1AA" |
| `pc_compact` | TEXT | Postcode without spaces | "SW1A1AA" |
| `latitude` | REAL | WGS84 latitude | 51.501009 |
| `longitude` | REAL | WGS84 longitude | -0.141588 |
| `eastings` | INTEGER | OS grid reference | 529090 |
| `northings` | INTEGER | OS grid reference | 180371 |
| `country` | TEXT | Country name | "England" |
| `country_code` | TEXT | Country GSS code | "E92000001" |
| `admin_district` | TEXT | District name | "Westminster" |
| `admin_district_id` | TEXT | District GSS code | "E09000033" |
| `admin_county` | TEXT | County name | NULL |
| `admin_county_id` | TEXT | County GSS code | NULL |
| `admin_ward` | TEXT | Ward name | "St James's" |
| `admin_ward_id` | TEXT | Ward GSS code | "E05009392" |
| `parish` | TEXT | Parish name | NULL |
| `parish_id` | TEXT | Parish GSS code | NULL |
| `constituency` | TEXT | Parliamentary constituency | "Westminster North" |
| `constituency_id` | TEXT | Constituency GSS code | "E14000639" |
| `region` | TEXT | Government office region | "London" |
| `region_code` | TEXT | Region GSS code | "E12000007" |
| `european_electoral_region` | TEXT | European region | "London" |
| `european_electoral_region_code` | TEXT | European region code | "E15000007" |
| `ccg` | TEXT | Sub ICB Location name | "NHS North West London" |
| `ccg_id` | TEXT | Sub ICB Location code | "E38000256" |
| `primary_care_trust` | TEXT | PCT name | "Westminster" |
| `primary_care_trust_code` | TEXT | PCT code | "E16000149" |
| `nhs_ha` | TEXT | NHS health authority | "London" |
| `nhs_ha_code` | TEXT | NHS HA code | "E19000003" |
| `lsoa` | TEXT | Lower Super Output Area | "Westminster 018A" |
| `lsoa_id` | TEXT | LSOA GSS code | "E01004736" |
| `msoa` | TEXT | Middle Super Output Area | "Westminster 018" |
| `msoa_id` | TEXT | MSOA GSS code | "E02000977" |
| `nuts` | TEXT | Statistical region name | "Westminster" |
| `nuts_id` | TEXT | ITL GSS code | "E09000033" |
| `pfa` | TEXT | Police force area | "Metropolitan Police" |
| `pfa_id` | TEXT | PFA GSS code | "E23000001" |
| `ced` | TEXT | County electoral division | NULL |
| `ced_id` | TEXT | CED GSS code | NULL |
| `quality` | INTEGER | Positional accuracy (1-10) | 1 |
| `date_introduced` | TEXT | Introduction date (YYYYMM) | "198001" |
| `incode` | TEXT | Inward code | "1AA" |
| `outcode` | TEXT | Outward code | "SW1A" |

**Table: `metadata`**
- Processing statistics and configuration info

### Python Data Format

Alternative output from `onspd_processor.py`:

```python
POSTCODE_DATA = {
    "SW1A 1AA": {
        'coordinates': {
            'latitude': 51.501009,
            'longitude': -0.141588,
            'eastings': 529090,
            'northings': 180371,
        },
        'administrative': {
            'country': 'England',
            'admin_district': 'Westminster',
            'admin_ward': "St James's",
            'parish': None,
            'constituency': 'Westminster North',
            'region': 'London',
        },
        'healthcare': {
            'ccg': 'NHS North West London',
            'primary_care_trust': 'Westminster',
            'nhs_ha': 'London',
        },
        'statistical': {
            'lsoa': 'Westminster 018A',
            'msoa': 'Westminster 018',
            'nuts': 'Westminster',
        },
        'codes': {
            'country_code': 'E92000001',
            'admin_district_id': 'E09000033',
            # ... all GSS codes
        },
        'quality': 1,
        'date_introduced': '198001',
        'incode': '1AA',
        'outcode': 'SW1A',
    }
}
```

## Performance Characteristics

### Processing Performance
- **Speed**: ~8,650 postcodes/second
- **Memory**: 50MB chunks, scales to any dataset size
- **Time**: ~3.5 minutes for complete UK dataset (1.8M postcodes)

### Database Performance
- **File Size**: 958MB (optimized with indexes)
- **Single Lookup**: <1ms average
- **Spatial Queries**: <100ms for nearest neighbor
- **Bulk Queries**: ~100k postcodes/second

### Coverage Statistics
- **Total Postcodes**: 1,799,395 (active only)
- **Coordinate Coverage**: 99.3% (1,786,367 postcodes)
- **Healthcare Coverage**: 99.5% (CCG/Sub ICB assignments)
- **Statistical Coverage**: 93.9% (NUTS/ITL assignments)
- **Administrative Coverage**: 99.9% (district assignments)

## Example Queries

### Single Postcode Lookup
```sql
SELECT postcode, latitude, longitude, country, admin_district 
FROM postcodes 
WHERE postcode = 'SW1A 1AA';
```

### Area Search
```sql
SELECT postcode, admin_district 
FROM postcodes 
WHERE admin_district = 'Westminster' 
LIMIT 10;
```

### Spatial Query (Nearest Postcodes)
```sql
SELECT postcode,
       (6371 * acos(cos(radians(51.5)) * cos(radians(latitude)) * 
       cos(radians(longitude) - radians(-0.1)) + 
       sin(radians(51.5)) * sin(radians(latitude)))) AS distance
FROM postcodes 
WHERE latitude IS NOT NULL 
  AND latitude BETWEEN 51.4 AND 51.6
  AND longitude BETWEEN -0.2 AND 0.0
ORDER BY distance 
LIMIT 10;
```

### Coverage Analysis
```sql
SELECT 
    country,
    COUNT(*) as postcode_count,
    COUNT(latitude) as with_coordinates,
    ROUND(COUNT(latitude) * 100.0 / COUNT(*), 1) as coord_coverage_pct
FROM postcodes 
GROUP BY country;
```

## Error Handling

### Common Issues
- **Missing CSV files**: Check ONSPD directory structure
- **Insufficient memory**: Reduce `--chunk-size` parameter  
- **Permission errors**: Ensure write access to output directory
- **Corrupted data**: Re-download ONSPD dataset

### Validation
Built-in validation checks:
- Coordinate consistency (lat/lon pair integrity)
- Lookup table resolution (GSS code → name mapping)
- Field coverage percentages
- Database index creation
- Query performance benchmarks

### Logs and Debugging
Enable verbose logging for troubleshooting:
```bash
python postcode_database_builder.py [args] --verbose
```

Logs include:
- Processing progress and speed
- Lookup table loading status
- Coordinate validation results
- Database creation statistics
- Performance benchmark results