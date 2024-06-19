import os
import json

from ..config import LOCAL_FOLDER, LOCAL_DB_FILE

# These functions are for loading/saving to local files when the USE_AWS environment variable is false
# LOCAL_FOLDER is based on an environment variable and will be the local location where we're storing files.
# LOCAL_DB_FILE is the local JSON file we're using as a stand-in for a nosql database like DynamoDB
# This probably wouldn't scale well, but since it is for a single user, it will probably be fine.

def get_local_folder():
    """
    Ensure the local folder exists and return its path.

    This function checks if the local folder exists, and if not, creates it.

    :return: The path to the local folder.
    """
    if not os.path.exists(LOCAL_FOLDER):
        os.makedirs(LOCAL_FOLDER)
    return LOCAL_FOLDER

def get_local_db():
    """
    Load the local database from a JSON file.

    This function checks if the local database file exists. If not, it creates
    an empty JSON file. It then reads and returns the contents of the file.

    :return: The contents of the local database as a dictionary.
    """
    if not os.path.exists(LOCAL_DB_FILE):
        with open(LOCAL_DB_FILE, 'w') as f:
            json.dump({}, f)
    with open(LOCAL_DB_FILE, 'r') as f:
        return json.load(f)

def save_local_db(data):
    """
    Save data to the local database JSON file.

    This function writes the provided data to the local database file in JSON format.

    :param data: The data to save to the local database.
    """
    with open(LOCAL_DB_FILE, 'w') as f:
        json.dump(data, f)
