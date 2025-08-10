# Test Suite Documentation

This directory contains comprehensive tests for the UK Postcodes Parsing library v2.0, covering both legacy functionality and new database-driven features.

## Test Structure

### Core Tests (Legacy)
- **`test_all.py`** - Original test suite covering core parsing functionality
  - Postcode parsing and validation
  - OCR error correction
  - Corpus text extraction
  - Component extraction (area, district, sector, etc.)
  - Fix distance calculations

### New Functionality Tests

#### `test_database_manager.py` 
**Cross-platform database management**
- Database download and verification
- Cross-platform path handling (Windows/Unix)
- Thread-safe singleton patterns
- Error handling (network failures, corruption)
- Cache management and cleanup

#### `test_postcode_database.py`
**Database operations and PostcodeResult**
- PostcodeResult dataclass functionality
- SQLite database queries and lookups
- Thread-local database connections
- Field mapping from database to user-friendly names
- Confidence scoring and distance calculations
- Database statistics and caching

#### `test_spatial_queries.py`
**Geographic and spatial functionality**
- Haversine distance calculations with known coordinates
- Nearest neighbor searches within radius
- Reverse geocoding (coordinates → postcode)
- Bounding box optimization
- Performance testing with realistic datasets
- Uses real London coordinates for validation

#### `test_api_functions.py`
**Clean API functions and error handling**
- All new API functions: `lookup_postcode`, `search_postcodes`, etc.
- Database unavailable scenarios (graceful fallbacks)
- Input validation and edge cases
- Import behavior and function availability
- Mock database testing

#### `test_integration.py`
**End-to-end workflows and cross-platform testing**
- Complete database setup workflows
- Cross-platform compatibility (Windows paths vs Unix)
- Concurrent access and thread safety
- Real-world usage patterns
- Memory management and connection pooling
- Error scenarios and fallback mechanisms

#### `test_backward_compatibility.py`
**Ensuring no breaking changes**
- All existing functions work unchanged
- Import patterns remain the same
- Function signatures and return types preserved
- SQLite fallback to Python file behavior
- Sorting and filtering patterns
- Exception handling behavior

#### `test_compatibility.py`
**Validation against postcodes.io reference data**
- Known postcode coordinate validation (M32 0JG, OX49 5NU)
- Reverse geocoding with postcodes.io test data
- Search ordering consistency (M1 vs M11, SE1 vs SE1P)  
- Distance calculations between known postcode pairs
- Case and space insensitive behavior validation
- Edge case handling (invalid postcodes, unreasonable searches)
- Spatial function accuracy using real-world test cases
- Uses MIT-licensed test data from postcodes.io for validation

## Test Categories

### Unit Tests (Fast, Isolated)
- Core parsing logic (no database required)
- Database management classes (with mocked networks)
- PostcodeResult dataclass (with temporary test databases)
- Spatial calculations (with known test data)

**Run with:**
```bash
pytest tests/test_all.py tests/test_database_manager.py tests/test_postcode_database.py tests/test_backward_compatibility.py -v
```

### Integration Tests (Real Database Required)
- Real database download and setup validation
- Cross-platform database operations with actual ONSPD data
- End-to-end workflows with real postcodes
- Performance testing with full dataset
- Compatibility validation against postcodes.io reference data

**Run with:**
```bash
# Database setup happens automatically in GitHub Actions
# For local testing, database is auto-downloaded on first use

pytest tests/test_integration.py tests/test_api_functions.py tests/test_spatial_queries.py tests/test_compatibility.py -v
```

### All Tests (Comprehensive)
```bash
pytest tests/ -v
```

## Test Data

### Reference Data (data/ directory)
- **bulk_geocoding.json** - Reverse geocoding test cases from postcodes.io
- **bulk_postcode.json** - Known postcode coordinate validation data
- **postcode_parse_test.csv** - Legacy parsing test data

### Unit Test Databases
Unit tests create temporary SQLite databases with known postcodes:
- **SW1A 1AA** (Parliament): 51.501009, -0.141588
- **SW1E 6LA** (Victoria): 51.494789, -0.134270  
- **SW1P 3AD** (Westminster): 51.498749, -0.138969
- **E3 4SS** (Tower Hamlets): 51.540300, -0.026000

### Compatibility Test Data
Real postcodes from postcodes.io (MIT licensed):
- **M32 0JG**: Eastings 379988, Northings 395476
- **OX49 5NU**: Eastings 464447, Northings 195647
- **CM8 1EF/1EU**: For reverse geocoding validation
- **M46 9WU/9XF**: For distance calculation testing

### Known Distances
- Parliament to Victoria: ~0.85km
- Parliament to Westminster Cathedral: ~0.15km
- London to Edinburgh: ~535km

### Administrative Areas
- **Westminster District**: Multiple postcodes for area queries
- **Cities of London and Westminster Constituency**: Boundary testing
- **NHS North West London**: Healthcare region testing

## Expected Test Behavior

### Database Unavailable Scenarios
When the SQLite database is not available (expected in CI without network):
- API functions return `None` or empty lists
- Graceful fallback to Python file lookup
- No exceptions thrown, just logged warnings
- Backward compatibility maintained

### Testing Approaches

#### Unit Tests with Temporary Databases
- **Fast execution**: Create small SQLite databases with known test data
- **Isolated testing**: No network dependencies, consistent test data
- **Logic validation**: Test database operations, PostcodeResult functionality
- **Examples**: SW1A 1AA, SW1E 6LA with known coordinates

#### Integration Tests with Real Database
- **Real-world validation**: Uses actual ONSPD database (2.8+ million postcodes)
- **Data accuracy**: Validates against postcodes.io reference data
- **Performance testing**: Tests with full dataset scale
- **Cross-platform**: Verifies behavior on Ubuntu/Windows

Both approaches ensure comprehensive coverage from unit logic to real-world accuracy.

## Running Tests in CI/CD

### GitHub Actions Matrix
```yaml
# Main test job - all OS/Python combinations (mocked)
test:
  strategy:
    matrix:
      os: [ubuntu-latest, windows-latest, macos-latest]  
      python-version: ["3.8", "3.9", "3.10", "3.11"]

# Database integration - limited matrix (real database)
database-integration:
  strategy:
    matrix:
      os: [ubuntu-latest, windows-latest]
      python-version: ["3.10"]
```

### Local Development
```bash
# Install test dependencies
pip install pytest pandas

# Run fast tests during development
pytest tests/test_all.py -v

# Run full test suite
pytest tests/ -v

# Run specific test categories
pytest tests/test_spatial_queries.py -v -k "haversine"
pytest tests/test_integration.py -v -k "cross_platform"
```

## Test Maintenance

### Adding New Tests
1. **Unit tests**: Add to appropriate existing file
2. **New functionality**: Create new test file following naming pattern
3. **Integration scenarios**: Add to `test_integration.py`
4. **Backward compatibility**: Add to `test_backward_compatibility.py`

### Mock Data Guidelines
- Use real UK postcodes with known coordinates
- Include edge cases (no coordinates, different regions)
- Test both valid and invalid postcodes
- Cover different postcode formats (A9 9AA, AA9A 9AA, etc.)

### Performance Expectations
- **Unit tests**: < 2 seconds total
- **Database operations**: < 5ms per lookup
- **Spatial queries**: < 50ms within 10km radius
- **Memory usage**: < 100MB peak during testing

This comprehensive test suite ensures v2.0 maintains 100% backward compatibility while thoroughly validating all new database-driven features.