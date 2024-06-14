# Copy the application directory into the container
#FROM python:3.9.19-alpine3.19
FROM python:3.11-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libopenblas-dev \
    python3-dev \
    libyaml-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip3 install -r requirements.txt

# Copy the application directory into the container
COPY app /app/app/


# Ensure the necessary scripts and requirements are copied
# COPY table_seeder.py /app/
# COPY user_seeder.py /app/


# Create a directory for logs
RUN mkdir -p /app/logs
# Make sure the log directory is writable
RUN chmod -R 777 /app/logs

# Ensure local_storage directory exists in the container
RUN mkdir -p /app/local_storage






#RUN python3 table_seeder.py
#RUN python3 user_seeder.py
# Comment this out if you do not want to execute AWS CLI command in container
#RUN aws --endpoint-url=http://localhost:4566 s3 mb s3://segbuilder

# Update the CMD to point to the main application entry point
CMD ["python3", "-m", "app.server"]