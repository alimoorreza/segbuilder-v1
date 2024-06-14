import json
import os
from werkzeug.security import generate_password_hash

def initialize_local_db():
    # Check if the local DB file exists
    if not os.path.exists("local_db.json"):
        # Create initial structure for the local DB file
        initial_data = {
            "users": {"local_user":generate_password_hash("password")},
            "projects": {"local_user":[]},
            "project-classes": {}
        }
        # Write the initial structure to the local DB file
        with open("local_db.json", 'w') as db_file:
            json.dump(initial_data, db_file, indent=4)
        print(f"Local DB file local_db.json created successfully.")
    else:
        print(f"Local DB file local_db.json already exists.")

initialize_local_db()
print("Local DB initialized successfully.")