
import logging
import os
import botocore
import shutil
from flask import url_for

from .aws_resources import get_s3_client, get_s3_resource
from .local_resources import get_local_folder
from ..config import USE_AWS

def load_file_from_s3(s3_path):
    s3_client = get_s3_client() 
    _, s3_bucket = get_s3_resource()
    s3_bucket_name = s3_bucket.name
    try:
        obj = s3_client.get_object(Bucket=s3_bucket_name,Key=s3_path)
        data = obj['Body'].read()
        return data
    except Exception as e:
        logging.debug("Error occurred while reading the file from S3: %s", e)
        return None
    
def load_file_from_filesystem(file_path):
    base_dir = get_local_folder()
    full_path = os.path.join(base_dir,file_path)
    try:
        with open(full_path, 'rb') as file:
            content = file.read()
        return content
    except Exception as e:
        logging.debug("Error occurred while reading the file from the filesystem: %s", e)
        return None

def load_file(path):
    if USE_AWS:
        return load_file_from_s3(path)
    else:
        return load_file_from_filesystem(path)
    
def write_file_to_s3(s3_path,data):
    s3_client = get_s3_client() 
    _, s3_bucket = get_s3_resource()
    s3_bucket_name = s3_bucket.name
    try:
        s3_client.put_object(Bucket=s3_bucket_name, Key=s3_path, Body=data)
    except Exception as e:
        logging.error("Error occurred while writing the file to S3: %s", e)

       

def write_file_to_filesystem(file_path,data):
    base_dir = get_local_folder()
    full_path = os.path.join(base_dir,file_path)
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # open the file
        with open(full_path, "wb") as file:
            file.write(data)
    except Exception as e:
        logging.error("Error occurred while writing the file to the filesystem: %s", e)


def write_file(path,data):
    if USE_AWS:
        write_file_to_s3(path,data)
    else:
        write_file_to_filesystem(path,data)


def file_exists_in_s3(s3_path):
    s3_client = get_s3_client() 
    _, s3_bucket = get_s3_resource()
    s3_bucket_name = s3_bucket.name
    try:
        response = s3_client.head_object(Bucket=s3_bucket_name, Key=s3_path)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            # The object does not exist.
            return False
        else:
            # Something else has gone wrong.
            logging.error("Unexpected error checking for S3 file: %s", e)
            raise

def file_exists_in_filesystem(file_path):
    base_dir = get_local_folder()
    full_path = os.path.join(base_dir, file_path)
    return os.path.exists(full_path)

def file_exists(path):
    if USE_AWS:
        return file_exists_in_s3(path)
    else:
        return file_exists_in_filesystem(path)
    
def serve_file_in_s3(s3path):
    s3_client = get_s3_client() 
    _, s3_bucket = get_s3_resource()
    s3_bucket_name = s3_bucket.name
    try:
        cover_image = s3_client.generate_presigned_url('get_object',
                                            Params={'Bucket': s3_bucket_name,
                                                    'Key': s3path},
                                            ExpiresIn=3600)
    except botocore.exceptions.NoCredentialsError as e:
        logging.error("SBDEBUG: NoCredentialsError")
        logging.error("%s",e)

def serve_file_locally(file_path):
    base_dir = get_local_folder()
    full_path = os.path.join(base_dir,file_path)
    return url_for('static', filename=full_path, _external=True)

def serve_file(path):
    if USE_AWS:
        return serve_file_in_s3(path)
    else:
        return serve_file_locally(path)
    

def get_files_in_s3_prefix(directory_path):
    s3_client = get_s3_client() 
    _, s3_bucket = get_s3_resource()
    s3_bucket_name = s3_bucket.name
    logging.debug("SBDEBUG: inside get_image_names")
    files = []
    logging.debug("SBDEBUG: about to connect to s3")
    paginator = s3_client.get_paginator('list_objects_v2') 
    logging.debug("SBDEBUG: got the paginator")
    result = paginator.paginate(Bucket=s3_bucket_name, Prefix=directory_path)
    for page in result:
        for obj in page.get('Contents', []):
            filename = obj['Key'][(len(directory_path)+1):]
            files.append(filename)
    logging.debug("SBDEBUG: here are the images read from s3"+str(files))
    return files

def get_files_in_local_directory(directory_path):
    base_dir = get_local_folder()
    full_path = os.path.join(base_dir, directory_path)
    files = []
    try:
        for root, dirs, filenames in os.walk(full_path):
            for filename in filenames:
                relative_path = os.path.relpath(os.path.join(root, filename), full_path)
                files.append(relative_path)
    except Exception as e:
        logging.error("Error occurred while listing files in the local directory: %s", e)
    logging.debug("SBDEBUG: here are the files read from the local filesystem: " + str(files))
    return files

def get_files_in_directory(directory_path):
    if USE_AWS:
        return get_files_in_s3_prefix(directory_path)
    else:
        return get_files_in_local_directory(directory_path)
    

def file_download_from_s3(remote_file,local_file):
    s3_client = get_s3_client() 
    _, s3_bucket = get_s3_resource()
    s3_bucket_name = s3_bucket.name
    try:
        s3_client.download_file(s3_bucket_name, remote_file, local_file)
        logging.debug(f"Successfully downloaded {remote_file} from S3 to {local_file}")
    except Exception as e:
        logging.error(f"Error occurred while downloading the file from S3: {e}")

def file_download_from_filesystem(remote_file, local_file):
    base_dir = get_local_folder()
    full_remote_path = os.path.join(base_dir, remote_file)
    try:
        shutil.copy(full_remote_path, local_file)
        logging.debug(f"Successfully copied {full_remote_path} to {local_file}")
    except Exception as e:
        logging.error(f"Error occurred while copying the file from the filesystem: {e}")

def file_download(remote_file, local_file):
    if USE_AWS:
        file_download_from_s3(remote_file, local_file)
    else:
        file_download_from_filesystem(remote_file, local_file)


