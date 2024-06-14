# SegBuilder

## Overview

SegBuilder is a Dash web application for labeling SAM-generated segmentations for downstream computer vision applications.

It can be configured for deployment to AWS or can be run locally with file-based storage for development and testing.

## Prerequisites

- Docker
- Docker Compose

## Configuration

The application can be configured to use either AWS services or local resources. This is controlled by the `USE_AWS` environment variable. You can edit the configuration in the `compose.yaml` file for either environment.

- `USE_AWS=True`: Use AWS services (DynamoDB, S3).
- `USE_AWS=False`: Use local resources (local file storage).

## Setup

1. Clone the repository:
    ```sh
    git clone <repository_url>
    cd <repository_directory>
    ```

2. When running locally for the first time, seed the database and users:
    * Local configuration:
        ```sh
        python3 table_seeder_local.py
        ```
    * AWS configuration: edit users as desired in `user_seeder.py` and run
        ```sh
        python3 table_seeder.py
        python3 user_seeder.py
        ```

2. Build and run the Docker containers:
    ```sh
    docker-compose up --build
    ```

## Accessing the Application

- The Dash web application will be accessible at `http://localhost:8050`.

## Environment Variables

The following environment variables are used to configure the application:

- `USE_AWS`: Set to `True` to use AWS services, or `False` to use local resources.
- `AWS_DEFAULT_REGION`: The AWS region to use (default: `us-east-2`). Set this if `USE_AWS` is `True`.
- `S3_BUCKET_NAME`: The name of the S3 bucket to use (default: `segbuilder`). Set this if `USE_AWS` is `True`.
- `LOCAL_FOLDER`: The local directory to use for file storage (default: `/app/local_storage`). Set this if `USE_AWS` is `False`.
- `LOCAL_DB_FILE`: The local file to use for the database (default: `/app/local_db.json`). Set this if `USE_AWS` is `False`.

## Running the Application

1. Start the application with Docker Compose:
    ```sh
    docker-compose up --build
    ```

2. The web application should be running and accessible at `http://localhost:8050`.

## Notes

- Ensure the local directories (`local_storage` and `local_db.json`) exist in the project root before starting the application.
- Modify the `docker-compose.yaml` and `Dockerfile` as needed to fit your specific use case and environment.


## Additional Commands

- To stop the application:
    ```sh
    docker-compose down
    ```

- To rebuild the application:
    ```sh
    docker-compose up --build
    ```

