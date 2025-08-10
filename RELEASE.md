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