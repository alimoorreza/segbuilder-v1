from flask_login import UserMixin, LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from botocore.exceptions import ClientError
import logging

#from ..resources import get_dynamodb_resource
from ..resources import get_db_item, update_db_item


# Flask-Login manager
login_manager = LoginManager()


class User(UserMixin):
    def __init__(self, username, password):
        self.id = username
        self.password = password #generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

@login_manager.user_loader
#def load_user(username,get_response_item=False):
def load_user(username):
    logging.debug("LOADUSER: username,  %s,  %s",username,type(username))
    #dynamodb = get_dynamodb_resource()
    #users_table = dynamodb.Table('users')
    #logging.debug("LOADUSER: users table from dynamo,  %s",users_table)
    try:
        #response = users_table.get_item(
        #   Key={
        #        'username': username
        #    }
        #)
        #logging.debug("LOADUSER: response,  %s",response)

        db_user_data = get_db_item(table_name="users",key_name="username",key_value=username)

        logging.debug("LOADUSER: db_user_data, %s",db_user_data)
    except ClientError as e:
        logging.debug("%s",e.response['Error']['Message'])
        return None
    else:

        if db_user_data:
            return User(db_user_data['username'], db_user_data['password'])

        #if 'Item' in response:
        #    if get_response_item:
        #        return response["Item"]
        #    else:
        #        user_data = response['Item']
        #        return User(user_data['username'], user_data['password'])
        else:
            return None
    #return users.get(username)


def change_password_in_db(username, new_password):
    #dynamodb = get_dynamodb_resource()
    #users_table = dynamodb.Table('users')

    new_password_hashed = generate_password_hash(new_password)
    try:
        update_db_item(table_name="users",key_name="username",key_value=username,item_name="password",item_value=new_password_hashed)
        # users_table.update_item(
        #     Key={
        #         'username': username
        #     },
        #     UpdateExpression='SET password = :val1',
        #     ExpressionAttributeValues={
        #         ':val1': new_password_hashed
        #     }
        # )
    except ClientError as e:
        print(e.response['Error']['Message'])
        return False

    return True