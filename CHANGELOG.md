# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.1] - 2024-12-XX

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

[Unreleased]: https://github.com/anirudhgangwal/uk-postcodes-parsing/compare/v2.0.1...HEAD
[2.0.1]: https://github.com/anirudhgangwal/uk-postcodes-parsing/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/anirudhgangwal/uk-postcodes-parsing/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/anirudhgangwal/uk-postcodes-parsing/releases/tag/v1.0.0