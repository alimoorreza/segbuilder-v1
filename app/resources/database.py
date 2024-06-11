from  app.config import USE_AWS
from .aws_resources import get_dynamodb_resource
from .local_resources import get_local_db, save_local_db
import logging
import datetime


def get_db_item_aws(table_name,key,key_value,default_return=None):
    dynamodb = get_dynamodb_resource()
    db_table = dynamodb.Table(table_name)
    response = db_table.get_item(Key={key:key_value})
    return_item = default_return
    if "Item" in response:
        return_item = response["Item"]
    return return_item

# design decision: allowing the key value to be a regular dictionary key 
# - not using the partition key with key value like DynamoDB uses
def get_db_item_local(table_name,key_value,default_return=None):
    local_db = get_local_db()
    db_table = local_db[table_name]
    return_item = default_return
    if key_value in db_table:
        return_item = db_table[key_value]
    return return_item

def get_db_item(table_name,key_name,key_value,default_return=None):
    if USE_AWS:
        return get_db_item_aws(table_name,key_name,key_value,default_return)
    else:
        return get_db_item_local(table_name,key_value,default_return)
    

def put_db_item_aws(table_name,key_name,key_value,item_name,item_value):
    dynamodb = get_dynamodb_resource()
    db_table = dynamodb.Table(table_name)
    db_table.put_item(Item={key_name:key_value,item_name:item_value})

# design decision: allowing the key value to be a regular dictionary key 
# - not using the partition key with key value like DynamoDB uses
def put_db_item_local(table_name,key_value,item_name,item_value):
    local_db = get_local_db()
    db_table = local_db[table_name]
    db_table[key_value] = {item_name:item_value}
    save_local_db(local_db)

def put_db_item(table_name,key_name,key_value,item_name,item_value):
    if USE_AWS:
        return put_db_item_aws(table_name,key_name,key_value,item_name,item_value)
    else:
        return put_db_item_local(table_name,key_value,item_name,item_value)
       

#!! should this return something?
def delete_db_item_aws(table_name,key_name,key_value):
    dynamodb = get_dynamodb_resource()
    db_table = dynamodb.Table(table_name)
    db_table.delete_item(Key={key_name: key_value})

#!! should this return something?
def delete_db_item_local(table_name,key_value):
    local_db = get_local_db()
    db_table = local_db[table_name]
    if key_value in db_table:
        db_table.remove(key_value)

#!! should this return something?
def delete_db_item(table_name,key_name,key_value):
    if USE_AWS:
        return delete_db_item_aws(table_name,key_name,key_value)
    else:
        return delete_db_item_local(table_name,key_value)


def update_db_item_aws(table_name,key_name,key_value,item_name,item_value):
    dynamodb = get_dynamodb_resource()
    db_table = dynamodb.Table(table_name)

    db_table.update_item(
        Key = {key_name:key_value},
        UpdateExpression="set #item = :val",
        ExpressionAttributeNames={
            "#item": item_name
        },
        ExpressionAttributeValues={
            ':val': item_value
        }
    )

def update_db_item_local(table_name,key_value,item_name,item_value):
    put_db_item_local(table_name,key_value,item_name,item_value)

def update_db_item(table_name,key_name,key_value,item_name,item_value):
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
    