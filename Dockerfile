# ------------------------------------------------------------------------------
# Build Stage: Install C-build tools & compile dependencies
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libudev-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ------------------------------------------------------------------------------
# Final Runtime Stage: Ultra-lean image without build tools
# ------------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal udev runtime library only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libudev1 \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-compiled Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source code
COPY src/ ./src/
COPY main.py .

RUN mkdir -p /app/logs

CMD ["python", "-u", "main.py"]