FROM docker.io/library/python:3.14.0-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY aiweather/ ./aiweather/
COPY static/ ./static/
COPY config/ ./config/

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "aiweather:app", "--host", "0.0.0.0", "--port", "8000"]
