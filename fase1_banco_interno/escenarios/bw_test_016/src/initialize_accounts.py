import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['LEDGER_TABLE'])

def handler(event, context):
    table.put_item(Item={'account_id': 'A', 'balance': 1000})
    table.put_item(Item={'account_id': 'B', 'balance': 500})
    return {
        'statusCode': 200,
        'body': json.dumps({'status': 'ready'})
    }