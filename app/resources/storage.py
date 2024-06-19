
import logging
import os
import botocore
import shutil
from flask import url_for
import shutil

from .aws_resources import get_s3_client, get_s3_resource
from .local_resources import get_local_folder
from ..config import USE_AWS

# This file contains the functions for doing various filesystem operations with either
# AWS resources (S3) or the local file system.
# For each operation, we have one AWS and one local funcion,
# and then there is a wrapper that determines which to call based on the
# USE_AWS environment variable.

def load_file_from_s3(s3_path):
    """
    Load a file from S3 storage.

    This function uses the S3 client to retrieve the file specified by the S3 path from the S3 bucket.
    It reads the file content and returns it. If an error occurs during the process, it logs the error
    and returns None.

    :param s3_path: The S3 path of the file to load.
    :return: The file content as bytes, or None if an error occurs.
    """
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
    """
    Load a file from the local filesystem.

    This function retrieves the file specified by the file path from the local folder.
    It reads the file content and returns it. If an error occurs during the process, it logs the error
    and returns None.

    :param file_path: The path of the file to load from the local filesystem.
    :return: The file content as bytes, or None if an error occurs.
    """
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
    """
    Load a file from either S3 or the local filesystem based on the configuration.

    This function checks the USE_AWS flag to determine whether to load the file from
    S3 storage or from the local filesystem. It delegates the loading process to the 
    appropriate function based on this decision.

    :param path: The path of the file to load.
    :return: The file content as bytes, or None if an error occurs.
    """
    if USE_AWS:
        return load_file_from_s3(path)
    else:
        return load_file_from_filesystem(path)
    
def write_file_to_s3(s3_path,data):
    """
    Write a file to S3 storage.

    This function uses the S3 client to put the file specified by the S3 path into the S3 bucket.
    If an error occurs during the process, it logs the error.

    :param s3_path: The S3 path where the file will be written.
    :param data: The data to be written to the file.
    """
    s3_client = get_s3_client() 
    _, s3_bucket = get_s3_resource()
    s3_bucket_name = s3_bucket.name
    try:
        s3_client.put_object(Bucket=s3_bucket_name, Key=s3_path, Body=data)
    except Exception as e:
        logging.error("Error occurred while writing the file to S3: %s", e)

       

def write_file_to_filesystem(file_path,data):
    """
    Write a file to the local filesystem.

    This function writes the data to the file specified by the file path in the local folder.
    It ensures that the directory exists before writing the file. If an error occurs during 
    the process, it logs the error.

    :param file_path: The path where the file will be written in the local filesystem.
    :param data: The data to be written to the file.
    """
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
    """
    Write a file to either S3 or the local filesystem based on the configuration.

    This function checks the USE_AWS flag to determine whether to write the file to
    S3 storage or to the local filesystem. It delegates the writing process to the 
    appropriate function based on this decision.

    :param path: The path where the file will be written.
    :param data: The data to be written to the file.
    """
    if USE_AWS:
        write_file_to_s3(path,data)
    else:
        write_file_to_filesystem(path,data)


def file_exists_in_s3(s3_path):
    """
    Check if a file exists in S3 storage.

    This function uses the S3 client to check if the file specified by the S3 path exists in the S3 bucket.
    It returns True if the file exists, and False if it does not. If an unexpected error occurs, it logs the error
    and raises an exception.

    :param s3_path: The S3 path of the file to check.
    :return: True if the file exists, False otherwise.
    """
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
    """
    Check if a file exists in the local filesystem.

    This function checks if the file specified by the file path exists in the local folder.

    :param file_path: The path of the file to check in the local filesystem.
    :return: True if the file exists, False otherwise.
    """
    base_dir = get_local_folder()
    full_path = os.path.join(base_dir, file_path)
    return os.path.exists(full_path)

def file_exists(path):
    """
    Check if a file exists, either in S3 or the local filesystem based on the configuration.

    This function checks the USE_AWS flag to determine whether to check for the file in
    S3 storage or in the local filesystem. It delegates the check to the appropriate 
    function based on this decision.

    :param path: The path of the file to check.
    :return: True if the file exists, False otherwise.
    """
    if USE_AWS:
        return file_exists_in_s3(path)
    else:
        return file_exists_in_filesystem(path)
    
def serve_file_in_s3(s3path):
    """
    Generate a presigned URL to serve a file from S3 storage.

    This function uses the S3 client to generate a presigned URL for the file specified
    by the S3 path. The URL is valid for one hour. If the credentials are missing or 
    invalid, it logs the error and returns a default image URL.

    We are mostly using this so we can display an image from S3 as the src or an html img tag.

    :param s3path: The S3 path of the file to serve.
    :return: The presigned URL for the file, or a default image URL if an error occurs.
    """
    s3_client = get_s3_client() 
    _, s3_bucket = get_s3_resource()
    s3_bucket_name = s3_bucket.name

    try:
        cover_image = s3_client.generate_presigned_url('get_object',
                                            Params={'Bucket': s3_bucket_name,
                                                    'Key': s3path},
                                            ExpiresIn=3600)
        return cover_image
    except botocore.exceptions.NoCredentialsError as e:
        logging.error("SBDEBUG: NoCredentialsError")
        logging.error("%s",e)
        return "assets/eyelogo.png"

def serve_file_locally(file_path):
    """
    Serve a file from the local filesystem.

    This function copies the file specified by the file path to the static directory so it can
    be used/displayed from flask. If the directories do not exist, it creates them.

    :param file_path: The path of the file to serve in the local filesystem.
    :return: The URL to serve the file.
    """
    base_dir = get_local_folder()
    full_path = os.path.join(base_dir,file_path)
    logging.debug("In serve_file_locally")
    logging.debug("\tfull_path %s",full_path)

    static_path = os.path.join("app","static",full_path[1:])
    logging.debug("\tstatic_path %s",static_path)

    dir = os.path.dirname(full_path)
    logging.debug("\tdir %s",dir)

    static_dir = os.path.dirname(static_path)
    logging.debug("\tstatic_dir %s",static_dir)
    
    # Ensure the directory exists
    os.makedirs(static_dir, exist_ok=True)
    shutil.copyfile(full_path, static_path)

    #return static_path 
    return url_for('static', filename=full_path, _external=True)

def serve_file(path):
    """
    Serve a file, either from S3 or the local filesystem based on the configuration.

    This function checks the USE_AWS flag to determine whether to serve the file from
    S3 storage or from the local filesystem. It delegates the serving process to the 
    appropriate function based on this decision.

    :param path: The path of the file to serve.
    :return: The URL to serve the file.
    """
    if USE_AWS:
        return serve_file_in_s3(path)
    else:
        return serve_file_locally(path)
    

def get_files_in_s3_prefix(directory_path):
    """
    List files in an S3 directory.

    This function uses the S3 client to list files in the specified S3 directory path.
    It retrieves a paginator to handle large result sets and appends the filenames
    to a list, which is then returned.

    :param directory_path: The S3 directory path to list files from.
    :return: A list of filenames in the specified S3 directory.
    """
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
    """
    List files in a local directory.

    This function lists files in the specified local directory path.
    It walks the directory tree and appends the relative file paths
    to a list, which is then returned.

    :param directory_path: The local directory path to list files from.
    :return: A list of filenames in the specified local directory.
    """
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
    """
    List files in a directory, either in S3 or the local filesystem based on the configuration.

    This function checks the USE_AWS flag to determine whether to list files from
    an S3 directory or a local directory. It delegates the listing process to the 
    appropriate function based on this decision.

    :param directory_path: The directory path to list files from.
    :return: A list of filenames in the specified directory.
    """
    if USE_AWS:
        return get_files_in_s3_prefix(directory_path)
    else:
        return get_files_in_local_directory(directory_path)
    

def file_download_from_s3(remote_file,local_file):
    """
    Download a file from S3 storage to the local filesystem.

    This function uses the S3 client to download the file specified by the remote
    S3 path to the local path. If an error occurs during the process, it logs the error.

    :param remote_file: The S3 path of the file to download.
    :param local_file: The local path where the file will be saved.
    """
    s3_client = get_s3_client() 
    _, s3_bucket = get_s3_resource()
    s3_bucket_name = s3_bucket.name
    try:
        s3_client.download_file(s3_bucket_name, remote_file, local_file)
        logging.debug(f"Successfully downloaded {remote_file} from S3 to {local_file}")
    except Exception as e:
        logging.error(f"Error occurred while downloading the file from S3: {e}")

def file_download_from_filesystem(remote_file, local_file):
    """
    Copy a file from the local filesystem to another location in the local filesystem.

    This function copies the file specified by the remote file path to the local path.
    If an error occurs during the process, it logs the error.

    This function is kinda silly since we don't really need to "download" anything
    since it is already on the local machine, but we're including it so that all of the
    UI features work when running locally

    :param remote_file: The path of the file to copy from in the local filesystem.
    :param local_file: The path where the file will be copied to in the local filesystem.
    """
    base_dir = get_local_folder()
    full_remote_path = os.path.join(base_dir, remote_file)
    try:
        shutil.copy(full_remote_path, local_file)
        logging.debug(f"Successfully copied {full_remote_path} to {local_file}")
    except Exception as e:
        logging.error(f"Error occurred while copying the file from the filesystem: {e}")

def file_download(remote_file, local_file):
    """
    Download or copy a file, either from S3 or the local filesystem based on the configuration.

    This function checks the USE_AWS flag to determine whether to download the file
    from S3 storage or copy it from another location in the local filesystem. It delegates
    the operation to the appropriate function based on this decision.

    :param remote_file: The path of the file to download or copy.
    :param local_file: The local path where the file will be saved or copied.
    """
    if USE_AWS:
        file_download_from_s3(remote_file, local_file)
    else:
        file_download_from_filesystem(remote_file, local_file)


