# UK Postcodes Parsing

[![Test](https://github.com/anirudhgangwal/ukpostcodes/actions/workflows/test.yml/badge.svg)](https://github.com/anirudhgangwal/ukpostcodes/actions/workflows/test.yml)
[![Upload Python Package](https://github.com/anirudhgangwal/ukpostcodes/actions/workflows/python-publish.yml/badge.svg)](https://github.com/anirudhgangwal/ukpostcodes/actions/workflows/python-publish.yml)

**Extract UK postcodes from text and get rich geographic data.** The only Python library that combines intelligent text parsing with comprehensive postcode database lookup.

Perfect for **document processing**, **OCR applications**, **address validation**, and **location services**.

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
- **796MB database** with automatic download and cross-platform storage

### 📍 **Spatial Queries & Analysis**
- **Find nearest postcodes** to any coordinates
- **Reverse geocoding**: coordinates → nearest postcode
- **Distance calculations** between postcodes using Haversine formula
- **Area searches**: get all postcodes in districts, constituencies, etc.

### ⚡ **Zero Dependencies & High Performance**
- **Pure Python**: Uses only standard library, no external dependencies
- **Automatic setup**: Database downloads on first use
- **Cross-platform**: Windows, macOS, Linux support
- **Thread-safe**: Concurrent access supported

## Installation & Setup

```bash
pip install uk-postcodes-parsing
```

The postcode database (~796MB) downloads automatically on first use:

**Storage Locations:**
- **Windows**: `%APPDATA%\uk_postcodes_parsing\postcodes.db`
- **macOS/Linux**: `~/.uk_postcodes_parsing/postcodes.db`

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
westminster = ukp.get_area_postcodes("district", "Westminster", limit=1000000)
print(f"Westminster district has {len(westminster)} postcodes")

# Search by constituency
constituency = ukp.get_area_postcodes("constituency", "Cities of London and Westminster")
print(f"Constituency has {len(constituency)} postcodes")

# Get all postcodes in a specific outcode
sw1a_postcodes = ukp.get_outcode_postcodes("SW1A")
print(f"SW1A outcode has {len(sw1a_postcodes)} postcodes")
```

### 🛠️ OCR Error Correction & Text Processing

Advanced text processing for OCR and document digitization:

```python
import uk_postcodes_parsing as ukp

# OCR often confuses similar characters
ocr_text = "Contact office at SW1A OAA or try EH16 50Y for Scotland"

# Parse with error correction
postcodes = ukp.parse_from_corpus(ocr_text, attempt_fix=True)

for pc in postcodes:
    print(f"Original: '{pc.original}'")
    print(f"Corrected: '{pc.postcode}'")
    print(f"Confidence: {pc.fix_distance} (0=perfect, negative=corrected)")
    print(f"Valid: {pc.is_in_ons_postcode_directory}")
    print()

# For uncertain cases, get all possible corrections
uncertain_text = "OOO 4SS"  # Multiple possible fixes
all_options = ukp.parse_from_corpus(
    uncertain_text, 
    attempt_fix=True, 
    try_all_fix_options=True
)

print(f"Possible corrections for '{uncertain_text}':")
for option in all_options:
    print(f"  {option.postcode} (confidence: {option.fix_distance})")
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

## Complete API Reference

### Text Parsing Functions
```python
# Extract postcodes from text
postcodes = ukp.parse_from_corpus(text, attempt_fix=False, try_all_fix_options=False)

# Parse single postcode  
postcode = ukp.parse(postcode_string, attempt_fix=False)

# Check if postcode is valid
is_valid = ukp.is_in_ons_postcode_directory(postcode_string)
```

### Rich Lookup Functions  
```python
# Get comprehensive postcode data
result = ukp.lookup_postcode(postcode_string)  # Returns PostcodeResult or None

# Search by prefix
results = ukp.search_postcodes(query, limit=10)  # Returns List[PostcodeResult]

# Get postcodes in administrative areas
results = ukp.get_area_postcodes(area_type, area_value, limit=None)
# area_type: "district", "constituency", "region", "country", etc.
```

### Spatial Query Functions
```python  
# Find nearest postcodes
results = ukp.find_nearest(latitude, longitude, radius_km=10, limit=10)
# Returns List[Tuple[PostcodeResult, distance]]

# Reverse geocoding
result = ukp.reverse_geocode(latitude, longitude)  # Returns PostcodeResult or None

# Get postcodes by outcode
results = ukp.get_outcode_postcodes(outcode)  # Returns List[PostcodeResult]
```

### Database Management
```python
# Setup database (usually automatic)
success = ukp.setup_database(force_redownload=False)

# Get database info
info = ukp.get_database_info()
```

## Data Fields

Each `PostcodeResult` contains 25+ fields:

**Geographic:**
- `latitude`, `longitude` (99.3% coverage)
- `eastings`, `northings` (British National Grid)

**Administrative:**  
- `district`, `county`, `region`, `country`
- `ward`, `parish`, `constituency`

**Healthcare:**
- `healthcare_region`, `nhs_health_authority`

**Statistical:**
- `lower_output_area`, `middle_output_area`

**Postal:**
- `postcode`, `incode`, `outcode`

See full field list in API documentation.

## Advanced Features

### Performance & Threading
- **Thread-safe**: Use from multiple threads safely
- **Connection pooling**: Efficient database access
- **Caching**: Outcode queries cached for performance

### Error Handling
- **Graceful fallback**: Falls back to Python set if database unavailable (for parsing capability only)  

## Migration from v1.x

v2.0 is **100% backward compatible**. All existing code continues to work unchanged.

**New capabilities** (use these for new code):
```python
# v2.0 - Recommended import pattern
import uk_postcodes_parsing as ukp

# All functions available at top level
postcodes = ukp.parse_from_corpus(text)
result = ukp.lookup_postcode("SW1A 1AA") 
nearest = ukp.find_nearest(51.5, -0.14)
```

**Legacy imports** (still work):
```python  
# v1.x - Still supported
from uk_postcodes_parsing import ukpostcode
from uk_postcodes_parsing.fix import fix
```

## Contributing & Development

### Local development

```
# Install library in dev mode
pip install -e .

# Local changes take immediate effect
```



### Running Tests
```bash
# Install test dependencies
pip install pytest

# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/test_compatibility.py -v  # Validation tests
pytest tests/test_spatial_queries.py -v  # Spatial functionality
```

### Documentation
- [ONSPD Usage Guide](docs/ONSPD_USAGE_GUIDE.md) - Database creation
- [ONSPD Technical Guide](docs/ONSPD_TECHNICAL_GUIDE.md) - Technical details
- [Test Documentation](tests/README.md) - Testing approach

## Data Source & Updates

- **Source**: ONS Postcode Directory (ONSPD) - February 2024
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

**How we differ:**
- **Text extraction focus**: Advanced OCR error correction and corpus parsing
- **Python-native**: Pure Python implementation with no external dependencies
- **Offline-first**: Local database with automatic setup, no API dependencies
- **Document processing**: Optimized for batch text processing and document digitization

### ONS (Office for National Statistics)

All postcode data is derived from the [ONS Postcode Directory](https://geoportal.statistics.gov.uk/datasets/ons-postcode-directory-latest-centroids/about) under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

### AI Assisted disclosure

This project leveraged AI-assisted development tools.

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