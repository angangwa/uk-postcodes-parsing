# UK Postcodes Parsing

[![Test](https://github.com/anirudhgangwal/ukpostcodes/actions/workflows/test.yml/badge.svg)](https://github.com/anirudhgangwal/ukpostcodes/actions/workflows/test.yml)
[![Upload Python Package](https://github.com/anirudhgangwal/ukpostcodes/actions/workflows/python-publish.yml/badge.svg)](https://github.com/anirudhgangwal/ukpostcodes/actions/workflows/python-publish.yml)
[![Test PyPI Release](https://github.com/angangwa/uk-postcodes-parsing/actions/workflows/test-pypi-release.yml/badge.svg)](https://github.com/angangwa/uk-postcodes-parsing/actions/workflows/test-pypi-release.yml)

**Extract UK postcodes from text and get rich geographic data.** The only Python library that combines intelligent text parsing with comprehensive postcode database lookup.

Perfect for **document processing**, **OCR applications**, **address validation**, and **location services**.

🚀 **Lightweight & Fast**: Core text parsing and ONSPD validation requires no database. Rich geographic data requires a one-time small download.

**[Stats](https://clickpy.clickhouse.com/dashboard/uk-postcodes-parsing)**

## Quick Start

```bash
pip install uk-postcodes-parsing
```

**30-second example** - Extract postcodes from text and get enhanced data:

```python
import uk_postcodes_parsing as ukp

# Extract postcodes from any text (emails, documents, OCR results)
text = "Please send the report to our London office at SW1A 1AA or Manchester at M1 1AD"
postcodes = ukp.parse_from_corpus(text)

# Get rich geographic data for each postcode found
for pc in postcodes:
    enhanced = ukp.lookup_postcode(pc.postcode)
    if enhanced:
        print(f"{pc.postcode}: {enhanced.district}, {enhanced.region}")
        print(f"  📍 {enhanced.latitude:.3f}, {enhanced.longitude:.3f}")
        print(f"  🏛️ {enhanced.constituency}")

# Output:
# SW1A 1AA: Westminster, London
#   📍 51.501, -0.142
#   🏛️ Cities of London and Westminster
# M1 1AD: Manchester, North West
#   📍 53.484, -2.245
#   🏛️ Manchester Central
```

## ✨ Key Features

### 🔍 **Intelligent Text Parsing**
- **Extract postcodes from any text**: emails, documents, OCR results
- **OCR error correction**: Automatically fixes common mistakes (O↔0, I↔1, etc.)
- **Accurate parsing**: Handles all UK postcode formats and variations
- **Confidence scoring**: Know how reliable each extracted postcode is

### 🗺️ **Rich Geographic Database** (1.8M Postcodes, Feb 2025)
- **1.8M active UK postcodes** with comprehensive metadata
- **99.3% coordinate coverage** - latitude/longitude for nearly all postcodes
- **25+ data fields per postcode**: administrative, political, healthcare, statistical
- **Smart download**: 40MB compressed download, expands to ~700MB with optimized indices for fast queries

### 📍 **Spatial Queries & Analysis**
- **Find nearest postcodes** to any coordinates
- **Reverse geocoding**: coordinates → nearest postcode
- **Distance calculations** between postcodes using Haversine formula
- **Area searches**: get all postcodes in districts, constituencies, etc.

### ⚡ **Zero Dependencies & High Performance**
- **Pure Python**: Uses only standard library, no external dependencies
- **Fast validation**: Basic postcode validation without database dependency
- **Cross-platform**: Windows, macOS, Linux support
- **Thread-safe**: Concurrent access supported

## Setup

Full database and compressed database available in each [Release](https://github.com/angangwa/uk-postcodes-parsing/releases).

**Smart database Download:**
- **Interactive environments** (terminal, Jupyter): Prompts before downloading
- **Non-interactive environments**: Set `UK_POSTCODES_AUTO_DOWNLOAD=1` for automatic downloads (scripts, CI/CD)

**Storage Locations:**
- **Windows**: `%APPDATA%\uk_postcodes_parsing\postcodes.db`
- **macOS/Linux**: `~/.uk_postcodes_parsing/postcodes.db`

**Using Custom Database:**
```python
# Use a locally-built database instead of downloading
ukp.setup_database(local_db_path='/path/to/your/postcodes.db')

# Or set environment variable for database path
export UK_POSTCODES_DB_PATH=/path/to/your/postcodes.db

# Enable automatic downloads (for CI/CD, scripts)
export UK_POSTCODES_AUTO_DOWNLOAD=1
```

## Usage Examples

### 🔍 Text Parsing → Enhanced Lookup (Complete Workflow)

The most powerful feature - extract postcodes from messy text and get rich data:

```python
import uk_postcodes_parsing as ukp

# Real-world example: Extract from email/document
document = """
Dear Customer,

Your orders will be shipped to:
- London Office: SW1A 1AA (next to Big Ben)
- Manchester Branch: M1 1AD
- Edinburgh Office: EH1 1AD (city center)

For OCR'd text with errors: "Please send to SW1A OAA" (O instead of 0)

Advanced OCR with multiple fixes: "Send to EH16 50Y or M1 IAD"
"""

# Extract all postcodes
postcodes = ukp.parse_from_corpus(document, attempt_fix=True)
print(f"Found {len(postcodes)} postcodes:\n")

# Get comprehensive data for each
for pc in postcodes:
    enhanced = ukp.lookup_postcode(pc.postcode)
    if enhanced:
        print(f"🏠 {pc.postcode}")
        print(f"   📍 Location: {enhanced.district}, {enhanced.region}")
        print(f"   🗺️ Coordinates: {enhanced.latitude:.3f}, {enhanced.longitude:.3f}")
        print(f"   🏛️ Constituency: {enhanced.constituency}")
        print(f"   🏥 Healthcare: {enhanced.healthcare_region}")
        if pc.fix_distance < 0:  # Was corrected
            print(f"   ⚠️  Fixed from: {pc.original}")
        print()

# Advanced OCR: Get all possible corrections for uncertain text
uncertain_postcodes = ukp.parse_from_corpus("OOO 4SS", attempt_fix=True, try_all_fix_options=True)
print(f"Possible corrections: {[p.postcode for p in uncertain_postcodes]}")
```

### 🗺️ Direct Postcode Lookup

Get comprehensive data for known postcodes:

```python
import uk_postcodes_parsing as ukp

result = ukp.lookup_postcode("SW1A 1AA")
if result:
    print(f"Postcode: {result.postcode}")
    print(f"Coordinates: {result.latitude}, {result.longitude}")
    print(f"District: {result.district}")
    print(f"County: {result.county}")
    print(f"Region: {result.region}")
    print(f"Country: {result.country}")
    print(f"Constituency: {result.constituency}")
    print(f"Healthcare Region: {result.healthcare_region}")

# Convert to dictionary for APIs/JSON
data = result.to_dict()
print(f"API Response: {data}")
```

### 📍 Spatial Queries & Distance

Find postcodes near coordinates or other postcodes:

```python
import uk_postcodes_parsing as ukp

# Find nearest postcodes to coordinates (e.g., GPS location)
lat, lon = 51.5014, -0.1419  # Parliament Square, London
nearest = ukp.find_nearest(lat, lon, radius_km=1, limit=5)

print("Nearest postcodes:")
for postcode, distance in nearest:
    print(f"{postcode.postcode}: {distance:.2f}km - {postcode.district}")

# Reverse geocoding - coordinates to postcode
postcode = ukp.reverse_geocode(lat, lon)
print(f"Closest postcode: {postcode.postcode}")

# Distance between postcodes
london = ukp.lookup_postcode("SW1A 1AA")  # Parliament
edinburgh = ukp.lookup_postcode("EH16 5AY")  # Edinburgh city center
if london and edinburgh:
    distance = london.distance_to(edinburgh)
    print(f"London to Edinburgh: {distance:.1f}km")
```

### 🔎 Search & Area Queries

Search and filter postcodes by various criteria:

```python
import uk_postcodes_parsing as ukp

# Search postcodes by prefix
results = ukp.search_postcodes("SW1A", limit=5)
print(f"Found {len(results)} postcodes starting with SW1A")

# Get all postcodes in administrative areas
westminster = ukp.get_area_postcodes("district", "Westminster", limit=1_000_000)
print(f"Westminster district has {len(westminster)} postcodes")

# Search by constituency
constituency = ukp.get_area_postcodes("constituency", "Cities of London and Westminster")
print(f"Constituency has {len(constituency)} postcodes")

# Get all postcodes in a specific outcode
sw1a_postcodes = ukp.get_outcode_postcodes("SW1A")
print(f"SW1A outcode has {len(sw1a_postcodes)} postcodes")
```


### 🔧 Regex-Based Validation Utilities

For lightweight validation without database dependency, use the postcode_utils module:

```python
from uk_postcodes_parsing.postcode_utils import (
    is_valid, to_normalised, to_outcode, to_incode,
    to_area, to_district, to_sector, to_unit
)

# Basic validation (regex-only, no database needed)
print(is_valid("SW1A 1AA"))  # True
print(is_valid("INVALID"))   # False

# Extract postcode components
postcode = "SW1A 1AA"
print(to_outcode(postcode))    # "SW1A"
print(to_incode(postcode))     # "1AA"
print(to_area(postcode))       # "SW"
print(to_district(postcode))   # "SW1"
print(to_sector(postcode))     # "SW1A 1"
print(to_unit(postcode))       # "AA"

# Normalize formatting
print(to_normalised("sw1a1aa"))  # "SW1A 1AA"
```

### 📊 Database Management & Info

Control database setup and get statistics:

```python
import uk_postcodes_parsing as ukp

# Get database information
info = ukp.get_database_info()
print(f"Database has {info['record_count']:,} postcodes")
print(f"Database size: {info['size_mb']:.1f} MB")
print(f"Source: {info['metadata']['source_date']}")

# Explicit database setup (usually automatic)
success = ukp.setup_database()
if success:
    print("Database ready!")

# Force redownload if needed (rare)
ukp.setup_database(force_redownload=True)

# Get detailed statistics
from uk_postcodes_parsing.postcode_database import PostcodeDatabase
db = PostcodeDatabase()
stats = db.get_statistics()

print(f"Total postcodes: {stats['total_postcodes']:,}")
print(f"With coordinates: {stats['with_coordinates']:,}")
print(f"Coverage: {stats['coordinate_coverage_percent']}%")
print(f"Countries: {stats['countries']}")
```

## API Reference

**Text Parsing**: `parse_from_corpus()`, `parse()`, `is_in_ons_postcode_directory()`
**Rich Lookup**: `lookup_postcode()`, `search_postcodes()`, `get_area_postcodes()`
**Spatial Queries**: `find_nearest()`, `reverse_geocode()`, `get_outcode_postcodes()`
**Database**: `setup_database()`, `get_database_info()`

## Data Fields

Each `PostcodeResult` contains 25+ fields:

**Geographic**: `latitude`, `longitude`, `eastings`, `northings` (99.3% coverage)
**Administrative**: `district`, `county`, `region`, `country`, `constituency`
**Healthcare**: `healthcare_region`, `nhs_health_authority`
**Statistical**: `lower_output_area`, `middle_output_area`
**Postal**: `postcode`, `incode`, `outcode`

## Environment Configuration

### Environment Variables

**`UK_POSTCODES_AUTO_DOWNLOAD`**
- **Purpose**: Enable automatic database downloads without prompts
- **Values**: `1`, `true`, `yes` (case-insensitive) to enable
- **Use case**: CI/CD pipelines, automated scripts, serverless functions
```bash
export UK_POSTCODES_AUTO_DOWNLOAD=1
```

**`UK_POSTCODES_DB_PATH`**
- **Purpose**: Use custom database file instead of downloading
- **Value**: Absolute path to your `.db` file
- **Use case**: Custom-built databases, offline environments
```bash
export UK_POSTCODES_DB_PATH=/path/to/custom/postcodes.db
```

### Download Behavior

**Interactive Environments** (Terminal, Jupyter):
- Prompts user before downloading: "Download 40MB database? [y/N]"
- Shows download progress and setup time
- One-time setup, cached locally

**Non-Interactive Environments** (Scripts, CI/CD):
- Provides clear error with setup instructions
- Use `UK_POSTCODES_AUTO_DOWNLOAD=1`
- Prevents unexpected bandwidth usage

## Contributing & Development

```bash
# Install in development mode
pip install -e .

# Run tests
pip install pytest && pytest tests/ -v

# pre-commit install
```

**Database Creation**: [ONSPD Usage Guide](docs/ONSPD_USAGE_GUIDE.md) | [Technical Guide](docs/ONSPD_TECHNICAL_GUIDE.md)

## Data Source & Updates

- **Source**: ONS Postcode Directory (ONSPD) - February 2025
- **Coverage**: All active UK postcodes including Channel Islands, Isle of Man
- **License**: Data derived using postcodes.io extraction methodology (MIT License)
- **Updates**: Database can be regenerated with newer ONSPD releases using included tools

## Acknowledgments

### postcodes.io

This library was originally inspired by the excellent work at [postcodes.io](https://postcodes.io) by [Ideal Postcodes](https://github.com/ideal-postcodes). While postcodes.io focuses on providing a comprehensive REST API service, this library evolved to specialize in **text parsing and document processing** use cases.

**Key contributions from postcodes.io:**
- **Database processing logic**: Our ONSPD data processing pipeline is based on their proven methodology
- **Test data**: Reference test cases adapted from their validation suite (MIT License)
- **Field mappings**: Administrative area mappings and data structure insights

**How this library differ:**

- **Python-native**: Pure Python implementation with no external dependencies
- **Text extraction focus**: Text corpus parsing
- **Offline-first**: Local database with automatic setup, no API dependencies
- **Document processing**: Optimized for batch text processing and document digitization

### ONS (Office for National Statistics)

All postcode data is derived from the [ONS Postcode Directory](https://geoportal.statistics.gov.uk/datasets/ons-postcode-directory-latest-centroids/about) under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).


## License

### Software License

This software is released under the **MIT License**. Free for commercial and non-commercial use.

See [LICENSE](LICENSE) file for full terms.

### Data License

This library uses the **ONS Postcode Directory (ONSPD)** dataset, which carries different licensing terms:

#### Great Britain Postcodes
- **License**: UK Open Government Licence v3.0
- **Usage**: ✅ Free for both commercial and non-commercial use
- **Requirement**: Must acknowledge ONS as data source

#### Northern Ireland Postcodes (BT postcodes)
- **Non-commercial use**: ✅ Free under ONSPD licence terms
- **Commercial use**: ✅ Permitted for "Internal Business Use" under [End User Licence](https://www.ons.gov.uk/file?uri=/methodology/geography/licences/lpsenduserlicenceoct11_tcm77-278044.doc)
- **Other commercial use**: Requires separate licence from Land and Property Services NI

#### Summary for Most Users
- **Personal/Research**: ✅ All data free to use
- **Internal Business**: ✅ All data free for internal company use
- **Public-facing Commercial**: ✅ Great Britain data free, Northern Ireland may require licence

⚠️ **Important**: This is a best-effort summary. For authoritative licensing information and compliance with your specific use case, please consult the official [ONS licensing documentation](https://www.ons.gov.uk/methodology/geography/licences) and seek legal advice if needed.

**Data provided "as is" without warranty**
