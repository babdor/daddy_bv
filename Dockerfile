FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for build tools and udev serial access
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libudev-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/
COPY main.py .

# Create logs directory inside container
RUN mkdir -p /app/logs

# Run the application
CMD ["python", "-u", "main.py"]