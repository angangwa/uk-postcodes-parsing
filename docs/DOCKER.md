# Docker Usage Guide

The UK Postcodes API is available as a Docker image for easy deployment.

## Quick Start

```bash
# Run the latest version
docker run -p 8000:8000 anirudhgangwal/uk-postcodes-parsing:latest

# Run a specific version
docker run -p 8000:8000 anirudhgangwal/uk-postcodes-parsing:v2.1.0
```

The API will be available at `http://localhost:8000`

## Docker Compose

```yaml
version: '3.8'
services:
  uk-postcodes-api:
    image: anirudhgangwal/uk-postcodes-parsing:latest
    ports:
      - "8000:8000"
    restart: unless-stopped
```

## Multi-Platform Support

The Docker image supports multiple architectures:
- **linux/amd64** (Intel/AMD 64-bit)
- **linux/arm64** (ARM 64-bit, Apple Silicon, AWS Graviton)

## Image Details

- **Base**: Python 3.11-slim
- **Size**: ~1.3GB (includes full database)
- **Security**: Runs as non-root user
- **Database**: Pre-loaded SQLite database
- **Startup**: Instant (no download required)

## API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Example Usage

```bash
# Health check
curl http://localhost:8000/health

# Lookup a postcode
curl http://localhost:8000/postcodes/SW1A%201AA

# Find nearest postcodes
curl -X POST http://localhost:8000/spatial/nearest \
  -H "Content-Type: application/json" \
  -d '{"latitude": 51.5014, "longitude": -0.1419, "radius_km": 1}'
```