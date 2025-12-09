FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY viewer/ ./viewer/
COPY Files/ ./Files/
COPY output/ ./output/

# Copy environment file if exists
COPY .env* ./

# Expose port
EXPOSE 8081

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ITR_VIEWER_PORT=8081
ENV ITR_VIEWER_HOST=0.0.0.0

# Run the viewer
CMD ["python", "viewer/server.py"]
