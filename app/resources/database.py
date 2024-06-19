from  app.config import USE_AWS
from .aws_resources import get_dynamodb_resource
from .local_resources import get_local_db, save_local_db
import logging
import datetime

# This file contains the functions for doing CRUD operations with either
# AWS resources (DynamoDB) or the DB file on the local file system.
# For each CRUD operation, we have one AWS and one local funciont,
# and then there is a wrapper that determines which to call based on the
# USE_AWS environment variable.


def get_db_item_aws(table_name,key,key_value,default_return=None):
    """
    Retrieve an item from an AWS DynamoDB table.

    This function connects to the DynamoDB resource, retrieves the specified table,
    and attempts to get the item with the given key and key value. If the item is
    not found, it returns the default return value.

    :param table_name: The name of the DynamoDB table.
    :param key: The key of the item to retrieve.
    :param key_value: The value of the key for the item to retrieve.
    :param default_return: The value to return if the item is not found.
    :return: The retrieved item, or the default return value if not found.
    """
    dynamodb = get_dynamodb_resource()
    db_table = dynamodb.Table(table_name)
    response = db_table.get_item(Key={key:key_value})
    return_item = default_return
    if "Item" in response:
        return_item = response["Item"]
    return return_item

# 
def get_db_item_local(table_name,key_value,default_return=None):
    """
    Retrieve an item from a local database.

    This function reads the local database JSON file, retrieves the specified table,
    and attempts to get the item with the given key value. If the item is not found,
    it returns the default return value.

    :param table_name: The name of the local database table.
    :param key_value: The key value for the item to retrieve.
    :param default_return: The value to return if the item is not found.
    :return: The retrieved item, or the default return value if not found.

    Note: 
    - design decision: allowing the key value to be a regular dictionary key 
    - not using the partition key with key value like DynamoDB uses
    """
    local_db = get_local_db()
    db_table = local_db[table_name]
    return_item = default_return
    if key_value in db_table:
        return_item = db_table[key_value]
    return return_item

def get_db_item(table_name,key_name,key_value,default_return=None):
    """
    Retrieve an item from the database, either AWS DynamoDB or local.

    This function checks the USE_AWS flag to determine whether to retrieve the item
    from an AWS DynamoDB table or from a local database. It delegates the retrieval
    to the appropriate function based on this decision.

    :param table_name: The name of the database table.
    :param key_name: The key of the item to retrieve (used only for AWS).
    :param key_value: The value of the key for the item to retrieve.
    :param default_return: The value to return if the item is not found.
    :return: The retrieved item, or the default return value if not found.
    """
    if USE_AWS:
        return get_db_item_aws(table_name,key_name,key_value,default_return)
    else:
        return get_db_item_local(table_name,key_value,default_return)
    

def put_db_item_aws(table_name,key_name,key_value,item_name,item_value):
    """
    Put an item into an AWS DynamoDB table.

    This function connects to the DynamoDB resource, retrieves the specified table,
    and puts the item with the given key and key value.

    :param table_name: The name of the DynamoDB table.
    :param key_name: The name of the key for the item.
    :param key_value: The value of the key for the item.
    :param item_name: The name of the attribute to put.
    :param item_value: The value of the attribute to put.
    """
    dynamodb = get_dynamodb_resource()
    db_table = dynamodb.Table(table_name)
    db_table.put_item(Item={key_name:key_value,item_name:item_value})

# design decision: allowing the key value to be a regular dictionary key 
# - not using the partition key with key value like DynamoDB uses
def put_db_item_local(table_name,key_value,item_name,item_value):
    """
    Put an item into a local database.

    This function reads the local database JSON file, retrieves the specified table,
    and puts the item with the given key value.

    :param table_name: The name of the local database table.
    :param key_value: The key value for the item.
    :param item_name: The name of the attribute to put.
    :param item_value: The value of the attribute to put.

    Note: 
    - design decision: allowing the key value to be a regular dictionary key 
    - not using the partition key with key value like DynamoDB uses
    """
    local_db = get_local_db()
    db_table = local_db[table_name]
    db_table[key_value] = {item_name:item_value}
    save_local_db(local_db)

def put_db_item(table_name,key_name,key_value,item_name,item_value):
    """
    Put an item into the database, either AWS DynamoDB or local.

    This function checks the USE_AWS flag to determine whether to put the item
    into an AWS DynamoDB table or into a local database. It delegates the put
    operation to the appropriate function based on this decision.

    :param table_name: The name of the database table.
    :param key_name: The name of the key for the item (used only for AWS).
    :param key_value: The value of the key for the item.
    :param item_name: The name of the attribute to put.
    :param item_value: The value of the attribute to put.
    """
    if USE_AWS:
        return put_db_item_aws(table_name,key_name,key_value,item_name,item_value)
    else:
        return put_db_item_local(table_name,key_value,item_name,item_value)
       

def delete_db_item_aws(table_name,key_name,key_value):
    """
    Delete an item from an AWS DynamoDB table.

    This function connects to the DynamoDB resource, retrieves the specified table,
    and deletes the item with the given key and key value.

    :param table_name: The name of the DynamoDB table.
    :param key_name: The name of the key for the item.
    :param key_value: The value of the key for the item.
    :return: The response from the DynamoDB delete operation.
    """
    dynamodb = get_dynamodb_resource()
    db_table = dynamodb.Table(table_name)
    response = db_table.delete_item(Key={key_name: key_value})
    return response

#!!TODO: check what the actual response from Dynamo is in the above function and
# emulate it with our return
def delete_db_item_local(table_name,key_value):
    """
    Delete an item from a local database.

    This function reads the local database JSON file, retrieves the specified table,
    and deletes the item with the given key value if it exists.

    :param table_name: The name of the local database table.
    :param key_value: The key value for the item.
    :return: True if the item was successfully deleted, False if the item was not found.
    """
    local_db = get_local_db()
    db_table = local_db[table_name]
    if key_value in db_table:
        db_table.remove(key_value)
        save_local_db(local_db)
        return True
    return False

def delete_db_item(table_name,key_name,key_value):
    """
    Delete an item from the database, either AWS DynamoDB or local.

    This function checks the USE_AWS flag to determine whether to delete the item
    from an AWS DynamoDB table or from a local database. It delegates the delete
    operation to the appropriate function based on this decision.

    :param table_name: The name of the database table.
    :param key_name: The name of the key for the item (used only for AWS).
    :param key_value: The value of the key for the item.
    :return: The response from the delete operation (AWS) or a boolean indicating success (local).
    """
    if USE_AWS:
        return delete_db_item_aws(table_name,key_name,key_value)
    else:
        return delete_db_item_local(table_name,key_value)


def update_db_item_aws(table_name,key_name,key_value,item_name,item_value):
    """
    Update an item in an AWS DynamoDB table.

    This function connects to the DynamoDB resource, retrieves the specified table,
    and updates the item with the given key and key value, setting the specified 
    attribute to the new value.

    :param table_name: The name of the DynamoDB table.
    :param key_name: The name of the key for the item.
    :param key_value: The value of the key for the item.
    :param item_name: The name of the attribute to update.
    :param item_value: The new value of the attribute.
    :return: The response from the DynamoDB update operation.
    """
    dynamodb = get_dynamodb_resource()
    db_table = dynamodb.Table(table_name)

    response = db_table.update_item(
        Key = {key_name:key_value},
        UpdateExpression="set #item = :val",
        ExpressionAttributeNames={
            "#item": item_name
        },
        ExpressionAttributeValues={
            ':val': item_value
        }
    )
    return response

def update_db_item_local(table_name,key_value,item_name,item_value):
    """
    Update an item in a local database.

    This function uses the put_db_item_local function to update the item in the local database.

    :param table_name: The name of the local database table.
    :param key_value: The key value for the item.
    :param item_name: The name of the attribute to update.
    :param item_value: The new value of the attribute.
    :return: True - need to check what AWS's response is and change this to emulate that
    """
    put_db_item_local(table_name,key_value,item_name,item_value)
    return True

def update_db_item(table_name,key_name,key_value,item_name,item_value):
    """
    Update an item in the database, either AWS DynamoDB or local.

    This function checks the USE_AWS flag to determine whether to update the item
    in an AWS DynamoDB table or in a local database. It delegates the update operation 
    to the appropriate function based on this decision.

    :param table_name: The name of the database table.
    :param key_name: The name of the key for the item (used only for AWS).
    :param key_value: The value of the key for the item.
    :param item_name: The name of the attribute to update.
    :param item_value: The new value of the attribute.
    :return: The response from the update operation (AWS) or True (local).
    """
    if USE_AWS:
        return update_db_item_aws(table_name,key_name,key_value,item_name,item_value)
    else:
        return update_db_item_local(table_name,key_value,item_name,item_value)


#!! Am I actually using this anywhere?
#!! should this be app_session or flask_sessions instead of sessions table?
def update_last_activity(session_id):

    if USE_AWS:
        update_db_item_aws("sessions","session_id",session_id,"last_activity",datetime.datetime.now().isoformat())
    else:
        update_db_item_local("sessions","session_id","last_activity",datetime.datetime.now().isoformat())
    