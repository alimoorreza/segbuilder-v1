import boto3
from werkzeug.security import check_password_hash, generate_password_hash
import json
from app.config import USE_AWS
from app.resources import put_db_item

if USE_AWS:
    # Get the service resource.
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2',aws_access_key_id= 'test',aws_secret_access_key= 'test', endpoint_url = 'http://localhost:4566')

    users_table = dynamodb.Table('users')
    #sessions_table = dynamodb.Table('sessions')
    projects_table = dynamodb.Table("projects")
    classes_table = dynamodb.Table("project-classes")

    print(users_table)
    #print(sessions_table)

    users_table.put_item(
        Item={
            'username': 'sean',
            'password': generate_password_hash('chen'),
        }
    )

    users_table.put_item(
        Item={
            'username': 'sameer',
            'password': generate_password_hash('chaudhary'),
        }
    )

    users_table.put_item(
        Item={
            'username': 'Md',
            'password': generate_password_hash('Reza'),
        }
    )

else:

    put_db_item(table_name="users",key_name="username",key_value="local_user",item_name="password",item_value=generate_password_hash("password"))
