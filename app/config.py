import os

# use the environment variables to determine whether we're using AWS or the local filesystem for storage
# if we're doing local deployment, find where the files should go
# default values are given if the environment variables don't exist

USE_AWS = os.getenv('USE_AWS', 'False') == 'True'
LOCAL_FOLDER = os.getenv('LOCAL_FOLDER', 'local_storage')
LOCAL_DB_FILE = os.getenv('LOCAL_DB_FILE', 'local_db.json')