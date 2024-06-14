import os
import boto3

def get_dynamodb_resource():
    region_name = os.getenv('AWS_DEFAULT_REGION', 'us-east-2')
    return boto3.resource(
        'dynamodb',
        region_name=region_name,
        #aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'), #looks for AWS_ACCESS_KEY_ID environment variable if it exists or just 'test' if it doesn't
        #aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
        #endpoint_url='http://localhost:4566'  # For local development
    )

def get_s3_resource():
    region_name = os.getenv('AWS_DEFAULT_REGION', 'us-east-2')
    s3 = boto3.resource(
        's3',
        region_name=region_name,
        #aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
        #aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
        #endpoint_url='http://localhost:4566'  # For local development
    )
    return s3, s3.Bucket(os.getenv('S3_BUCKET_NAME', 'segbuilder'))

def get_s3_client():
    region_name = os.getenv('AWS_DEFAULT_REGION', 'us-east-2')
    return boto3.client(
        's3', 
        region_name=region_name,
        #aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
        #aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
        #endpoint_url='http://localhost:4566'
    )

