import boto3
import time

#!!TODO: This setup file is untested - need to try it with a fresh AWS instance

# Configure DynamoDB resource using AWS credentials file
dynamodb = boto3.resource('dynamodb')

# Function to create a table
def create_table(table_name, key_schema, attribute_definitions, read_capacity=5, write_capacity=5):
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            ProvisionedThroughput={
                'ReadCapacityUnits': read_capacity,
                'WriteCapacityUnits': write_capacity
            }
        )
        # Wait until the table exists
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"Table {table_name} created successfully.")
    except Exception as e:
        print(f"Error creating table {table_name}: {str(e)}")
    return table

# Create 'users' table
create_table(
    table_name='users',
    key_schema=[
        {
            'AttributeName': 'username',
            'KeyType': 'HASH'  # Partition key
        }
    ],
    attribute_definitions=[
        {
            'AttributeName': 'username',
            'AttributeType': 'S'  # String type attribute
        }
    ],
    read_capacity=1,
    write_capacity=1
)

# Create 'projects' table
create_table(
    table_name='projects',
    key_schema=[
        {
            'AttributeName': 'username',
            'KeyType': 'HASH'  # Partition key
        }
    ],
    attribute_definitions=[
        {
            'AttributeName': 'username',
            'AttributeType': 'S'
        }
    ],
    read_capacity=1,
    write_capacity=1
)

# Create 'project-classes' table
create_table(
    table_name='project-classes',
    key_schema=[
        {
            'AttributeName': 'username-projectname',
            'KeyType': 'HASH'  # Partition key
        }
    ],
    attribute_definitions=[
        {
            'AttributeName': 'username-projectname',
            'AttributeType': 'S'
        }
    ],
    read_capacity=1,
    write_capacity=1
)

# Create 'flask_sessions' table
create_table(
    table_name='flask_sessions',
    key_schema=[
        {
            'AttributeName': 'id',
            'KeyType': 'HASH'  # Partition key
        }
    ],
    attribute_definitions=[
        {
            'AttributeName': 'id',
            'AttributeType': 'S'
        }
    ]
)

# Print table status
def print_table_status(table_name):
    try:
        table = dynamodb.Table(table_name)
        table.load()
        print(f"{table_name} table status: {table.table_status}")
    except Exception as e:
        print(f"Error loading table status for {table_name}: {str(e)}")

# Print the status of all tables
table_names = ['users', 'projects', 'project-classes', 'flask_sessions']
for table_name in table_names:
    print_table_status(table_name)