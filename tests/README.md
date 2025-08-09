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

## Test Categories

### Unit Tests (Fast, No Dependencies)
- Core parsing logic
- Database management classes (mocked)
- PostcodeResult dataclass
- Spatial calculations
- API function interfaces (mocked)

**Run with:**
```bash
pytest tests/test_all.py tests/test_database_manager.py tests/test_postcode_database.py -v
```

### Integration Tests (Database Required)
- Real database download and setup
- Cross-platform database operations  
- End-to-end workflows
- Performance testing

**Run with:**
```bash
# Setup database first
python -c "import uk_postcodes_parsing as ukp; ukp.setup_database()"

# Then run integration tests
pytest tests/test_integration.py tests/test_api_functions.py -v -k "not mock"
```

### All Tests (Comprehensive)
```bash
pytest tests/ -v
```

## Test Data

### Mock Databases
Tests create temporary SQLite databases with known postcodes:
- **SW1A 1AA** (Parliament): 51.501009, -0.141588
- **SW1E 6LA** (Victoria): 51.494789, -0.134270  
- **SW1P 3AD** (Westminster): 51.498749, -0.138969
- **E3 4SS** (Tower Hamlets): 51.540300, -0.026000

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

### Mock vs Real Testing
- **Mock tests**: Fast, reliable, test logic and error handling
- **Real database tests**: Verify actual data and network operations
- Both approaches ensure comprehensive coverage

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