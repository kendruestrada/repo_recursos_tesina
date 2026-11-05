import os
import time
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TRACKER_TABLE'])

def reserve_resource(resource_key, tx_id):
    start = time.time()
    ttl = int(time.time()) + 300

    while True:
        try:
            table.put_item(
                Item={
                    'resource_key': resource_key,
                    'tx_id': tx_id,
                    'timestamp': Decimal(str(time.time())),
                    'ttl': ttl
                },
                ConditionExpression='attribute_not_exists(resource_key)'
            )
            return True
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            time.sleep(0.1)

def release_resource(resource_key, tx_id):
    try:
        table.delete_item(
            Key={'resource_key': resource_key},
            ConditionExpression='tx_id = :tid',
            ExpressionAttributeValues={':tid': tx_id}
        )
    except:
        pass