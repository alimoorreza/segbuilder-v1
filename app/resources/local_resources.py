import os
import json

from ..config import LOCAL_FOLDER, LOCAL_DB_FILE

def get_local_folder():
    if not os.path.exists(LOCAL_FOLDER):
        os.makedirs(LOCAL_FOLDER)
    return LOCAL_FOLDER

def get_local_db():
    if not os.path.exists(LOCAL_DB_FILE):
        with open(LOCAL_DB_FILE, 'w') as f:
            json.dump({}, f)
    with open(LOCAL_DB_FILE, 'r') as f:
        return json.load(f)

def save_local_db(data):
    with open(LOCAL_DB_FILE, 'w') as f:
        json.dump(data, f)
