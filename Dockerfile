FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including WeasyPrint requirements)
RUN apt-get update && apt-get install -y \
    gcc \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
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
