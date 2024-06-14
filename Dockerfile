
FROM python:3.11-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libopenblas-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip3 install -r requirements.txt

# Copy the application directory into the container
COPY app /app/app/

# Create a directory for logs
RUN mkdir -p /app/logs

# Make sure the log directory is writable
RUN chmod -R 777 /app/logs

# Ensure local_storage directory exists in the container
RUN mkdir -p /app/local_storage

# Update the CMD to point to the main application entry point
CMD ["python3", "-m", "app.server"]