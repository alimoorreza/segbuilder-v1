import os
import json
import boto3
import logging
from app.config import USE_AWS, LOCAL_DB_FILE

def initialize_local_db():
    # Check if the local DB file exists
    if not os.path.exists(LOCAL_DB_FILE):
        # Create initial structure for the local DB file
        initial_data = {
            "users": [],
            "projects": [],
            "project-classes": []
        }
        # Write the initial structure to the local DB file
        with open(LOCAL_DB_FILE, 'w') as db_file:
            json.dump(initial_data, db_file, indent=4)
        logging.debug(f"Local DB file {LOCAL_DB_FILE} created successfully.")
    else:
        logging.debug(f"Local DB file {LOCAL_DB_FILE} already exists.")


if USE_AWS:
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2',aws_access_key_id= 'test',aws_secret_access_key= 'test', endpoint_url = 'http://localhost:4566')

    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'username',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'username',
                'AttributeType': 'S'  # String type attribute
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )

    # Wait until the table exists.
    table.meta.client.get_waiter('table_exists').wait(TableName='users')

    print(f"Table {table.table_name} created successfully.")

    # Create the 'projects' table
    table_projects = dynamodb.create_table(
        TableName='projects',
        KeySchema=[
            {
                'AttributeName': 'username',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'username',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )

    # Create the 'project-classes' table
    table_project_classes = dynamodb.create_table(
        TableName='project-classes',
        KeySchema=[
            {
                'AttributeName': 'username-projectname',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'username-projectname',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )

    # Create the 'app_session' table
    table_app_session = dynamodb.create_table(
        TableName='app_session',
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )

    # Create the 'flask_sessions' table
    table_flask_sessions = dynamodb.create_table(
        TableName='flask_sessions',
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )

    print("Projects table status:", table_projects.table_status)
    print("Project-Classes table status:", table_project_classes.table_status)
    print("App Session table status:", table_app_session.table_status)
    print("Flask Sessions table status:", table_flask_sessions.table_status)

else:

    # Initialize the local DB file with the required tables and schemas
    initialize_local_db()
    print("Local DB initialized successfully.")