# Docker Hub Setup Guide

This guide explains how to set up Docker Hub publishing for the UK Postcodes Parsing API.

## Prerequisites

1. Docker Hub account with repository `anirudhgangwal/uk-postcodes-parsing` created
2. GitHub repository with the following secrets configured

## Required GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret:

### 1. DOCKER_USERNAME
- **Name**: `DOCKER_USERNAME`
- **Value**: Your Docker Hub username (`anirudhgangwal`)

### 2. DOCKER_PASSWORD
- **Name**: `DOCKER_PASSWORD`
- **Value**: Your Docker Hub access token (NOT your password)

### How to create Docker Hub access token:
1. Log in to Docker Hub
2. Go to Account Settings → Security
3. Click "New Access Token"
4. Name: `github-actions-uk-postcodes`
5. Permissions: Read, Write, Delete
6. Copy the generated token and use it as `DOCKER_PASSWORD`

## Multi-Platform Support

The workflow builds images for:
- **linux/amd64** (Intel/AMD 64-bit)
- **linux/arm64** (ARM 64-bit, Apple Silicon, AWS Graviton)

This ensures compatibility across:
- Traditional x86_64 servers
- Apple Silicon Macs (M1/M2/M3)
- ARM-based cloud instances (AWS Graviton, etc.)

## Publishing Triggers

The Docker images are automatically built and published when:

### 1. Version Tags (Production)
```bash
git tag v1.0.0
git push origin v1.0.0
```
Creates tags: `v1.0.0`, `1.0`, `1`, `latest`

### 2. Main Branch (Latest)
```bash
git push origin main
```
Updates the `latest` tag

### 3. Manual Workflow Dispatch
- Go to Actions → "Build and Push Docker Image" → Run workflow
- Specify custom tag name

## Usage Examples

### Pull and run latest image:
```bash
docker run -p 8000:8000 anirudhgangwal/uk-postcodes-parsing:latest
```

### Pull specific version:
```bash
docker run -p 8000:8000 anirudhgangwal/uk-postcodes-parsing:v1.0.0
```

### Pull for specific platform:
```bash
# For ARM64 (Apple Silicon)
docker run --platform linux/arm64 -p 8000:8000 anirudhgangwal/uk-postcodes-parsing:latest

# For AMD64 (Intel)
docker run --platform linux/amd64 -p 8000:8000 anirudhgangwal/uk-postcodes-parsing:latest
```

## Docker Compose with Docker Hub image

Update your `docker-compose.yml`:

```yaml
version: '3.8'
services:
  uk-postcodes-api:
    image: anirudhgangwal/uk-postcodes-parsing:latest
    ports:
      - "8000:8000"
    environment:
      - UK_POSTCODES_AUTO_DOWNLOAD=0
    restart: unless-stopped
```

## Image Details

- **Base OS**: Ubuntu (official Python image)
- **Python Version**: 3.11
- **Architecture**: Multi-platform (amd64, arm64)
- **Database**: Pre-loaded SQLite database
- **Size**: ~200MB (compressed layers)
- **Security**: Runs as non-root user (`apiuser`)

## Verification

After publishing, verify the image works:

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test postcode lookup
curl http://localhost:8000/postcodes/SW1A%201AA
```

## Troubleshooting

### Build failures:
1. Check that `postcodes.db` exists in repository root
2. Verify GitHub secrets are correctly set
3. Ensure Docker Hub repository exists and is public

### Platform-specific issues:
```bash
# Check available platforms
docker buildx ls

# Inspect image platforms
docker manifest inspect anirudhgangwal/uk-postcodes-parsing:latest
```

### Access denied:
- Verify Docker Hub token has Read/Write permissions
- Check token hasn't expired
- Ensure repository exists and is accessible