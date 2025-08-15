# Release Process

This document describes how to create a new release of uk-postcodes-parsing.

## Prerequisites

1. Ensure all tests pass locally: `pytest tests/`
2. Update `CHANGELOG.md` with release notes
3. Ensure `postcodes.db` is up-to-date and committed with Git LFS

## Release Steps

### 1. Update Version

Manually update the version in two files:

```bash
# Edit pyproject.toml
version = "2.0.1"  # Update to new version

# Edit src/uk_postcodes_parsing/__init__.py
__version__ = "2.0.1"  # Update to match
```

### 2. Commit Changes

```bash
git add -A
git commit -m "Release v2.0.1"
```

### 3. Create and Push Tag

```bash
git tag v2.0.1
git push origin main
git push origin v2.0.1
```

### 4. Automated Release Process

Once the tag is pushed, GitHub Actions will automatically:

1. **Create GitHub Release**
   - Attach `postcodes.db` from repository (Git LFS)
   - Generate release notes

2. **Publish to PyPI**
   - Build Python package
   - Upload to PyPI

3. **Test Published Package**
   - Install from PyPI on multiple platforms (Ubuntu, Windows, macOS)
   - Run full test suite
   - Test Python 3.8, 3.10, and 3.12

4. **Automatic Rollback** (if tests fail)
   - Yank version from PyPI
   - Delete GitHub release
   - Create GitHub issue for tracking

## Manual Release (Alternative)

If you prefer to trigger manually:

```bash
# Use GitHub Actions workflow dispatch
# Go to Actions tab → Publish Release → Run workflow
# Enter tag: v2.0.1
```

## Rollback Process

If the automated rollback fails or you need to manually rollback:

### Yank from PyPI
```bash
pip install twine
twine yank uk-postcodes-parsing==2.0.1 --reason "Rollback: [reason]"
```

### Delete GitHub Release
1. Go to Releases page
2. Click on the release
3. Click "Delete" button

### Un-yank (if needed)
```bash
# To restore a yanked version
twine unyank uk-postcodes-parsing==2.0.1
```

## Database Updates

When ONSPD data is updated:

1. Download new ONSPD data from [ONS](https://geoportal.statistics.gov.uk/datasets/ons-postcode-directory-latest-centroids)
2. Build new database:
   ```bash
   cd onspd_tools
   python postcode_database_builder.py /path/to/onspd/multi_csv --output ../postcodes.db --validate
   ```
3. Verify database:
   ```bash
   python -c "
   import sqlite3
   conn = sqlite3.connect('postcodes.db')
   count = conn.execute('SELECT COUNT(*) FROM postcodes').fetchone()[0]
   print(f'Postcodes: {count:,}')
   "
   ```
4. Commit with Git LFS:
   ```bash
   git add postcodes.db
   git commit -m "Update database to ONSPD [Month Year]"
   ```

## Troubleshooting

### PyPI API Key Issues
- Ensure `PYPI_API_KEY` secret is set in GitHub repository settings
- Token must have upload and yank permissions

### Git LFS Issues
- Ensure `.gitattributes` includes: `postcodes.db filter=lfs diff=lfs merge=lfs -text`
- Run `git lfs track "postcodes.db"` if needed

### Test Failures
- Check GitHub Actions logs for specific failure
- Test locally with same Python version
- Ensure database is properly tracked in Git LFS

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 2.0.1)
- **MAJOR**: Breaking API changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Pre-release Versions

For experimental or testing releases, use pre-release suffixes:
- **Alpha**: `2.1.0a1`, `2.1.0a2` - Early development, may have bugs
- **Beta**: `2.1.0b1`, `2.1.0b2` - Feature complete, testing phase
- **Release Candidate**: `2.1.0rc1` - Final testing before stable release

## Pre-release Process

### When to Use Pre-releases

Use pre-releases for:
- **Major architectural changes** (like v2.1.0's 95% size reduction)
- **New features that need community testing**
- **Database schema changes**
- **Breaking changes** (even with major version bumps)

### Creating a Pre-release

#### 1. Update Version to Pre-release
```bash
# Edit pyproject.toml
version = "2.1.0a1"  # Alpha 1

# Edit src/uk_postcodes_parsing/__init__.py
__version__ = "2.1.0a1"
```

#### 2. Update Changelog
Add entry under `## [Unreleased]` or create new section:
```markdown
## [2.1.0a1] - 2025-08-15

### ⚠️ Alpha Release - Testing Only
- Major performance optimizations (95% size reduction)
- Please report issues: https://github.com/angangwa/uk-postcodes-parsing/issues

### Added
- XZ compression for database downloads
- Outcode-based sharding for lazy loading
- [... other changes ...]
```

#### 3. Commit and Tag
```bash
git add -A
git commit -m "Release v2.1.0a1 - Alpha release for community testing"
git tag v2.1.0a1
git push origin main
git push origin v2.1.0a1
```

#### 4. Automatic Pre-release Handling
The GitHub workflow automatically detects pre-releases and:
- ✅ Marks GitHub release as "Pre-release"
- ✅ Publishes to PyPI as pre-release
- ✅ Users must explicitly opt-in to install

### Pre-release Installation

**Users can install pre-releases with:**
```bash
# Install specific alpha version
pip install uk-postcodes-parsing==2.1.0a1

# Install latest pre-release (any alpha/beta/rc)
pip install uk-postcodes-parsing --pre

# Normal install still gets latest stable
pip install uk-postcodes-parsing  # Gets 2.0.4, not 2.1.0a1
```

### Pre-release Testing Cycle

#### Recommended Flow:
1. **Alpha Phase** (`2.1.0a1`, `2.1.0a2`, ...): Core changes, gather feedback
2. **Beta Phase** (`2.1.0b1`, `2.1.0b2`, ...): Feature complete, wider testing
3. **Release Candidate** (`2.1.0rc1`): Final testing, documentation review
4. **Stable Release** (`2.1.0`): Production ready

#### Example Multi-Alpha Cycle:
```bash
# Alpha 1 - Initial testing
version = "2.1.0a1"
git tag v2.1.0a1

# Alpha 2 - Fix critical issues from a1 feedback
version = "2.1.0a2"
git tag v2.1.0a2

# Beta 1 - Feature complete, broader testing
version = "2.1.0b1"
git tag v2.1.0b1

# Release Candidate - Final testing
version = "2.1.0rc1"
git tag v2.1.0rc1

# Stable release
version = "2.1.0"
git tag v2.1.0
```

### Promoting Pre-release to Stable

When ready to promote `2.1.0rc1` → `2.1.0`:

#### 1. Update Versions
```bash
# Edit pyproject.toml
version = "2.1.0"  # Remove pre-release suffix

# Edit src/uk_postcodes_parsing/__init__.py
__version__ = "2.1.0"
```

#### 2. Update Changelog
```markdown
## [2.1.0] - 2025-08-15

### 🚀 Major Performance & Size Optimizations
- Promoted from 2.1.0rc1 after successful community testing
- [... copy content from pre-release entries ...]
```

#### 3. Release as Stable
```bash
git add -A
git commit -m "Release v2.1.0 - Stable release"
git tag v2.1.0
git push origin main
git push origin v2.1.0
```

**Result:**
- `pip install uk-postcodes-parsing` now gets 2.1.0 (stable)
- All previous alphas/betas remain available but are superseded
- Pre-release testing data helps ensure stable release quality

### Pre-release Best Practices

#### Communication
- **Clear labeling**: Always mark as "Alpha/Beta/RC" in release notes
- **Issue tracking**: Encourage bug reports with pre-release version info
- **Breaking changes**: Document what might change before stable

#### Testing
- **Broader testing**: Ask community to test major changes
- **Real-world usage**: Get feedback on performance improvements
- **Edge cases**: Pre-releases help discover issues missed in CI

#### Version Management
- **No gaps**: Don't skip versions (a1 → a2 → a3, not a1 → a3)
- **Clear progression**: alpha → beta → rc → stable
- **Hotfixes**: Use patch versions on stable, not pre-releases

### Pre-release Rollback

If a pre-release has critical issues:

```bash
# Yank the problematic pre-release
pip install twine
twine yank uk-postcodes-parsing==2.1.0a1 --reason "Critical bug in database loading"

# Continue with next pre-release
version = "2.1.0a2"  # With fixes
git tag v2.1.0a2
```

**Note**: Pre-release issues are less critical since users must explicitly opt-in, but still yank if there are data corruption or security issues.