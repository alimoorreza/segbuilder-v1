from flask_login import UserMixin, LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from botocore.exceptions import ClientError
import logging
logging.basicConfig(filename='/app/logs/app.log', level=logging.DEBUG)

from ..resources import get_db_item, update_db_item

# Flask-Login manager
login_manager = LoginManager()

class User(UserMixin):
    """
    User class for managing user authentication.

    Attributes:
    - id (str): The username of the user.
    - password (str): The hashed password of the user.

    Methods:
    - check_password(password): Check if the provided password matches the stored password hash.
    """
    def __init__(self, username, password):
        """
        Initialize a new User instance.

        :param username: The username of the user.
        :param password: The hashed password of the user.
        """
        self.id = username
        self.password = password 

    def check_password(self, password):
        """
        Check if the provided password matches the stored password hash.

        :param password: The password to check.
        :return: True if the password matches, False otherwise.
        """
        #logging.debug("User.check_password: %s, %s",self.password,password)
        return check_password_hash(self.password["password"], password)

#def load_user(username,get_response_item=False):
@login_manager.user_loader
def load_user(username):
    """
    Load a user by username.

    This function is used by Flask-Login to retrieve a user object based on the username.

    :param username: The username to load.
    :return: The User object if found, None otherwise.
    """
    logging.debug("LOADUSER: username,  %s,  %s",username,type(username))

    try:
        password_hash = get_db_item(table_name="users",key_name="username",key_value=username)
        logging.debug("LOADUSER: password_hash, %s",password_hash)
    except ClientError as e:
        logging.debug("%s",e.response['Error']['Message'])
        return None
    else:

        if password_hash:
            return User(username, password_hash)
        else:
            return None
    #return users.get(username)


def change_password_in_db(username, new_password):
    """
    Change the user's password in the database.

    This function hashes the new password and updates the password hash in the database.

    :param username: The username of the user.
    :param new_password: The new password to set.
    :return: True if the password was successfully changed, False otherwise.
    """
    new_password_hashed = generate_password_hash(new_password)
    try:
        update_db_item(table_name="users",key_name="username",key_value=username,item_name="password",item_value=new_password_hashed)

    except ClientError as e:
        print(e.response['Error']['Message'])
        return False

    return True