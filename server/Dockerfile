# Multi-stage Dockerfile for UK Postcodes API Server
# Includes pre-loaded database for instant startup

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies and wget for downloading
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download full database with indices from GitHub releases
# This eliminates the need for Git LFS and ensures indices are present
RUN wget -q https://github.com/angangwa/uk-postcodes-parsing/releases/latest/download/postcodes.db \
    && echo "Database downloaded successfully (with indices)"

# Copy requirements first for better caching
COPY server/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UK_POSTCODES_AUTO_DOWNLOAD=0 \
    UK_POSTCODES_DB_PATH=/app/data/postcodes.db

# Create non-root user
RUN useradd -m -u 1000 apiuser

# Set working directory
WORKDIR /

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/apiuser/.local

# Make sure scripts in .local are usable
ENV PATH=/home/apiuser/.local/bin:$PATH

# Copy application code as a package
COPY --chown=apiuser:apiuser server/app/ /app/

# Create data directory
RUN mkdir -p /app/data && chown apiuser:apiuser /app/data

# Copy decompressed database from builder stage
COPY --from=builder --chown=apiuser:apiuser /app/postcodes.db /app/data/postcodes.db

# Note: Database already includes indices, so startup is immediate
# Image size: ~800MB but provides zero-delay startup and offline capability

# Switch to non-root user
USER apiuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]