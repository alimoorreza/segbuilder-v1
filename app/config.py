import os

USE_AWS = os.getenv('USE_AWS', 'True') == 'True'
LOCAL_FOLDER = os.getenv('LOCAL_FOLDER', 'local_storage')
LOCAL_DB_FILE = os.getenv('LOCAL_DB_FILE', 'local_db.json')