import os
import boto3

# These functions are wrappers for retrieving AWS resources that will be used
# when the USE_AWS environment variable is True. 

def get_dynamodb_resource():
    """
    Get the DynamoDB resource using boto3.

    This function retrieves the AWS region from environment variables and
    initializes a DynamoDB resource.

    :return: The DynamoDB resource.
    """
    region_name = os.getenv('AWS_DEFAULT_REGION', 'us-east-2')
    return boto3.resource(
        'dynamodb',
        region_name=region_name,
    )

def get_s3_resource():
    """
    Get the S3 resource and bucket using boto3.

    This function retrieves the AWS region and S3 bucket name from environment
    variables and initializes an S3 resource and bucket object.

    :return: A tuple containing the S3 resource and S3 bucket object.
    """
    region_name = os.getenv('AWS_DEFAULT_REGION', 'us-east-2')
    s3 = boto3.resource(
        's3',
        region_name=region_name,
    )
    return s3, s3.Bucket(os.getenv('S3_BUCKET_NAME', 'segbuilder'))

def get_s3_client():
    """
    Get the S3 client using boto3.

    This function retrieves the AWS region from environment variables and
    initializes an S3 client.

    :return: The S3 client.
    """
    region_name = os.getenv('AWS_DEFAULT_REGION', 'us-east-2')
    return boto3.client(
        's3', 
        region_name=region_name,
    )

