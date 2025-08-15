# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2025-08-15

### 🚀 Major Performance & Size Optimizations

#### **Massive Size Reductions**
- **Package size**: Reduced from 20MB to ~3MB (85% reduction) via outcode-based sharding
- **Download size**: Reduced from 797MB to 40MB (95% reduction) via XZ compression
- **Memory usage**: Reduced from 20MB to <1MB (>95% reduction) via lazy loading
- **Setup time**: Reduced from ~60s to ~12s (80% faster) via optimized workflow

#### **Smart Database Architecture**
- **XZ Compression**: Database now downloads as 40MB compressed file, expands to ~700MB with indices
- **Outcode Sharding**: Split monolithic postcode file into 2,977 outcode-specific files for lazy loading
- **Index Optimization**: Indices created automatically after decompression for optimal query performance
- **Backward Compatibility**: Both compressed (.db.xz) and full (.db) files available in releases

#### **Enhanced User Experience**
- **Core functionality works without database**: Basic postcode validation now uses lightweight outcode system
- **Environment-aware downloads**: Interactive prompts in terminals/Jupyter, clear instructions for CI/CD
- **URL security validation**: Added scheme validation for download security (addresses bandit B310)
- **Configurable size thresholds**: Made database verification thresholds configurable for future-proofing

### 🔧 Technical Improvements

#### **Logging Standardization**
- **Replaced custom logging**: Switched from custom implementation to standard Python `logging` module
- **NullHandler pattern**: Added proper handler to prevent "No handlers" warnings
- **Improved log levels**: Better categorization (DEBUG for fixes, WARNING for parse failures)

### 📚 Documentation Updates
- **README optimization**: Prominently featured lightweight design and database requirements
- **Size references**: Updated all documentation to reflect current optimized sizes
- **Setup clarity**: Clear explanation of when database download is needed vs. core functionality

### Migration Notes
- **100% backward compatible**: All existing APIs work unchanged
- **Automatic optimization**: Users get benefits with no code changes required
- **Environment variables**: Same configuration options work as before


## [2.0.4] - 2025-08-10

### Changed
- **BREAKING**: Minimum Python version requirement raised from 3.9 to 3.10
- Updated CI/CD to test Python 3.10, 3.11, 3.12, and 3.13
- Resolves Windows-specific SQLite spatial function compatibility issues

### Technical Notes
- Python 3.9 on Windows lacks SQLite math functions (acos, cos, sin, radians)
- Python 3.10+ on Windows consistently includes SQLite 3.35.0+ with math functions
- Python 3.9 reaches end-of-life in October 2025
- This change ensures reliable spatial queries across all platforms including Windows

## [2.0.3] - 2025-08-10

### Changed
- **BREAKING**: Minimum Python version requirement raised from 3.8 to 3.9
- Updated CI/CD to test Python 3.9, 3.10, 3.11, 3.12, and 3.13
- Resolves SQLite spatial function compatibility issues on older Python versions

### Technical Notes
- Python 3.8 reached end-of-life in October 2024
- Python 3.9+ includes SQLite 3.35.0+ with required math functions (acos, cos, sin, radians)
- This change enables reliable spatial queries across all supported platforms

## [2.0.2] - 2025-08-10

### Fixed
- GitHub Actions release workflow: manual yank process and longer PyPI availability wait
- Import placement in test files for better code organization
- Logging implementation to use proper logger instead of print statements
- Memory efficiency improvements in test suite
- Test data extraction for better code reusability

### Removed
- Legacy enhanced_postcode_db.py file that was using outdated thread-local storage pattern

## [2.0.1] - 2025-08-10

### Added
- Support for local database paths via `local_db_path` parameter
- Environment variable support (`UK_POSTCODES_DB_PATH`) for custom database location
- Automated release workflow with post-release testing and automatic rollback
- Comprehensive tests for local database functionality

### Changed
- Database connection pattern to connection-per-operation for better reliability
- Documentation updated to reflect streamlined 25-column schema
- File size from 958MB to 797MB with optimized schema

### Fixed
- Windows file locking issues with SQLite connections
- Test isolation issues between test modules
- GitHub Actions test failures on Ubuntu and Windows

## [2.0.0] - 2024-XX-XX

### Added
- SQLite database with 1.8M UK postcodes
- Rich postcode lookup with 25+ data fields
- Spatial queries and distance calculations
- Automatic database download on first use
- Cross-platform support (Windows, macOS, Linux)

### Changed
- Complete rewrite with database backend
- Zero external dependencies design
- Thread-safe implementation

## [1.0.0] - Initial Release

### Added
- Basic UK postcode parsing from text
- OCR error correction
- Set-based validation

[Unreleased]: https://github.com/angangwa/uk-postcodes-parsing/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/angangwa/uk-postcodes-parsing/compare/v2.0.4...v2.1.0
[2.0.4]: https://github.com/angangwa/uk-postcodes-parsing/compare/v2.0.3...v2.0.4
[2.0.3]: https://github.com/angangwa/uk-postcodes-parsing/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/angangwa/uk-postcodes-parsing/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/angangwa/uk-postcodes-parsing/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/angangwa/uk-postcodes-parsing/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/angangwa/uk-postcodes-parsing/releases/tag/v1.0.0