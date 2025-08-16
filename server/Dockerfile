# Multi-stage Dockerfile for UK Postcodes API Server
# Includes pre-loaded database for instant startup

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

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

# Create data directory and copy database
# The database should be in the parent directory (uk-postcodes-parsing root)
RUN mkdir -p /app/data && chown apiuser:apiuser /app/data
COPY --chown=apiuser:apiuser postcodes.db /app/data/postcodes.db

# Alternative: If using compressed database, uncomment below:
# COPY --chown=apiuser:apiuser ../postcodes.db.xz /app/data/postcodes.db.xz
# RUN apt-get update && apt-get install -y --no-install-recommends xz-utils && \
#     xz -d /app/data/postcodes.db.xz && \
#     apt-get remove -y xz-utils && \
#     apt-get autoremove -y && \
#     rm -rf /var/lib/apt/lists/*

# Switch to non-root user
USER apiuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]