# SegBuilder

## Overview

SegBuilder is a Dash web application for labeling SAM-generated segmentations for downstream computer vision applications.

It can be configured for deployment to AWS or can be run locally with file-based storage for development and testing.

## Prerequisites

- Python 3
- Docker
- Docker Compose

## Configuration

The application can be configured to use either AWS services or local resources for the database and file storage. This is controlled by the `USE_AWS` environment variable. You can edit the configuration in the `compose.yaml` file for either environment.

- `USE_AWS=True`: Use AWS services (DynamoDB, S3).
- `USE_AWS=False`: Use local resources (local file storage).

Note that `USE_AWS` does not control where the application runs - it doesn't automatically deploy it to a cloud web server environment.

### Environment Variables

The following environment variables are used to configure the application, set within `compose.yaml`:

- `USE_AWS`: Set to `True` to use AWS services, or `False` to use local resources.
- `AWS_DEFAULT_REGION`: The AWS region to use (default: `us-east-2`). Set this if `USE_AWS` is `True`.
- `S3_BUCKET_NAME`: The name of the S3 bucket to use (default: `segbuilder`). Set this if `USE_AWS` is `True`.
- `LOCAL_FOLDER`: The local directory to use for file storage (default: `/app/local_storage`). Set this if `USE_AWS` is `False`.
- `LOCAL_DB_FILE`: The local file to use for the database (default: `/app/local_db.json`). Set this if `USE_AWS` is `False`.

If deploying to AWS, you also need to set the location of your AWS credentials file. By default it assumes it is in `~/.aws`. It can be changed by editing this line of `compose.yaml`:

```
- ~/.aws:/root/.aws:ro  # Mount AWS credentials - necessary if USE_AWS is True
```

Ensure the local directories (`local_storage` and `local_db.json`) exist in the project root before starting the application.




## Setup for AWS Deployment

The following steps are needed when running for the first time. This assumes that you have DynamoDB and S3 services available in the AWS console with credentials stored in an AWS credentials file.

1. Clone the repository:
    ```sh
    git clone <repository_url>
    cd <repository_directory>
    ```

2. Seed the DynamoDB database with necessary tables:

    ```sh
    python3 table_seeder_aws.py
    ```

3. Create a SegaBuilder user:
    ```sh
    python3 create_user_aws.py
    ```

4. Build and run the Docker containers:
    ```sh
    docker-compose up --build
    ```

## Setup for local deployment

The following steps are needed when running locally for the first time. 

1. Clone the repository:
    ```sh
    git clone <repository_url>
    cd <repository_directory>
    ```
2. Install the Werkzeug package, which is needed to seed the local database:
    ```sh
    python3 -m pip install Werkzeug==2.3.4
    ```

3. Seed the database and create a local user with username `local_user` and password `password` (it can be changed inside the app):
    ```sh
    python3 table_seeder_local.py
    ```

4. Build and run the Docker containers:
    ```sh
    docker-compose up --build
    ```

## Accessing the Application

- When served in the local development server, the application will be accessible at `http://localhost:8050`.

## Running and Stopping the Application

- Start the application with Docker Compose:
    ```sh
    docker-compose up --build
    ```
- To stop the application:
    ```sh
    docker-compose down
    ```

2. The web application should be running and accessible at `http://localhost:8050`.
