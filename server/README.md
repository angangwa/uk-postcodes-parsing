# UK Postcodes FastAPI Server

A high-performance REST API server for UK postcode lookup, parsing, and spatial queries. Built with FastAPI and powered by the `uk-postcodes-parsing` library.

## Features

All features of the library exposed as as REST API.

## Quick Start

### Using Docker (Recommended)

```bash
# Build and run with Docker Compose (from project root)
docker-compose -f server/docker-compose.yml up

# Or build manually (from project root)
docker build -f server/Dockerfile -t uk-postcodes-api .
docker run -p 8000:8000 uk-postcodes-api
```

The API will be available at `http://localhost:8000`

### Local Development

```bash
# Install dependencies
pip install -r server/requirements.txt

# Run the server (from project root)
cd server
uvicorn app.main:app --reload

# Or directly
python -m app.main
```

## API Documentation

Once running, visit:
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Core Postcode Operations

#### Get Single Postcode
```http
GET /postcodes/{postcode}
```
Example: `GET /postcodes/SW1A 1AA`

Returns comprehensive data including coordinates, administrative areas, and metadata.

#### Search Postcodes
```http
POST /postcodes/search
```
```json
{
  "query": "SW1A",
  "limit": 10
}
```

#### Bulk Lookup
```http
POST /postcodes/bulk
```
```json
{
  "postcodes": ["SW1A 1AA", "SW1A 2AA", "E1 6AN"]
}
```

#### Validate Postcodes
```http
POST /postcodes/validate
```
```json
{
  "postcodes": ["SW1A 1AA", "INVALID", "E1 6AN"]
}
```

### Text Parsing

#### Parse Postcodes from Text
```http
POST /postcodes/parse
```
```json
{
  "text": "Send mail to SW1A 1AA or contact office at E1 6AN",
  "attempt_fix": true,
  "try_all_fix_options": false
}
```

Supports OCR error correction (e.g., O→0, I→1).

### Spatial Queries

#### Find Nearest Postcodes
```http
POST /spatial/nearest
```
```json
{
  "latitude": 51.5014,
  "longitude": -0.1419,
  "radius_km": 2,
  "limit": 10
}
```

#### Reverse Geocode
```http
POST /spatial/reverse-geocode
```
```json
{
  "latitude": 51.5014,
  "longitude": -0.1419
}
```

#### Calculate Distance
```http
POST /spatial/distance
```
```json
{
  "postcode1": "SW1A 1AA",
  "postcode2": "E1 6AN"
}
```

### Area Queries

#### Get Postcodes by Area
```http
GET /areas/{area_type}/{area_value}?limit=100
```

Supported area types:
- `country` - England, Scotland, Wales, Northern Ireland
- `region` - e.g., London, North West
- `district` - e.g., Westminster, Manchester
- `county` - e.g., Greater London, Lancashire
- `constituency` - Parliamentary constituencies
- `healthcare_region` - NHS regions

Example: `GET /areas/district/Westminster?limit=10`

#### Get Postcodes by Outcode
```http
GET /outcodes/{outcode}
```
Example: `GET /outcodes/SW1A`

### Health & Status

#### Health Check
```http
GET /health
```

#### Database Info
```http
GET /database/info
```

## Response Format

All successful responses return appropriate HTTP status codes and JSON data.

### Example Postcode Response
```json
{
  "postcode": "SW1A 1AA",
  "incode": "1AA",
  "outcode": "SW1A",
  "coordinates": {
    "latitude": 51.501009,
    "longitude": -0.141588,
    "eastings": 529090,
    "northings": 179645,
    "quality": 1
  },
  "administrative": {
    "country": "England",
    "region": "London",
    "county": null,
    "district": "Westminster",
    "ward": "St. James's",
    "parish": null,
    "constituency": "Cities of London and Westminster",
    "county_division": null
  },
  "healthcare": {
    "healthcare_region": "London",
    "nhs_health_authority": "NHS North West London",
    "primary_care_trust": null
  },
  "statistical": {
    "lower_output_area": "Westminster 018C",
    "middle_output_area": "Westminster 018",
    "statistical_region": null
  },
  "services": {
    "police_force": "Metropolitan Police"
  },
  "metadata": {
    "date_introduced": "1980-01-01"
  }
}
```

## Configuration

Environment variables:

```bash
# Database configuration
UK_POSTCODES_DB_PATH=/path/to/postcodes.db  # Custom database path
UK_POSTCODES_AUTO_DOWNLOAD=0                # Disable auto-download (when using Docker)

# API configuration
UK_POSTCODES_MAX_BULK_REQUESTS=100         # Max postcodes in bulk request
UK_POSTCODES_MAX_TEXT_LENGTH=10000         # Max text length for parsing
UK_POSTCODES_MAX_SEARCH_RESULTS=100        # Max search results
UK_POSTCODES_MAX_AREA_RESULTS=10000        # Max area query results

# CORS configuration (production)
UK_POSTCODES_CORS_ORIGINS=["https://yourdomain.com"]
```

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Production Deployment

### Docker Deployment

The Docker image includes:
- Pre-loaded database (no download needed)
- Non-root user for security
- Health checks
- Optimized multi-stage build

```bash
# Build production image (from project root)
docker build -f server/Dockerfile -t uk-postcodes-api:latest .

# Run with custom settings
docker run -d \
  -p 8000:8000 \
  -e UK_POSTCODES_CORS_ORIGINS='["https://yourdomain.com"]' \
  --name uk-postcodes-api \
  uk-postcodes-api:latest
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: uk-postcodes-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: uk-postcodes-api
  template:
    metadata:
      labels:
        app: uk-postcodes-api
    spec:
      containers:
      - name: api
        image: uk-postcodes-api:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

### Performance Considerations

- The SQLite database is optimized with indices for fast lookups
- Database is read-only, perfect for horizontal scaling
- Each container includes its own database copy
- No network latency for database queries

## Security

- Input validation on all endpoints
- Rate limiting headers supported (configure reverse proxy)
- CORS configuration for browser security
- Non-root Docker user
- No write operations on database

