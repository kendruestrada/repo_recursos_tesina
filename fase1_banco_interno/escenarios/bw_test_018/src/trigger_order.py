import json
import os
import boto3
import uuid
from decimal import Decimal

sfn = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')

STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']
TABLE_NAME = os.environ['TABLE_NAME']

def handler(event, context):
    
    body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
    
    order_id = str(uuid.uuid4())
    customer_email = body.get('customer_email', 'test@example.com')
    amount = Decimal(str(body.get('amount', 100.0)))
    
    
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(
        Item={
            'order_id': order_id,
            'status': 'pending',
            'customer_email': customer_email,
            'amount': amount
        }
    )
    
    
    execution_input = {
        'order_id': order_id,
        'customer_email': customer_email,
        'amount': float(amount)  
    }
    
    response = sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps(execution_input)
    )
    
    print(f"Started saga execution for order {order_id}: {response['executionArn']}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'order_id': order_id,
            'execution_arn': response['executionArn'],
            'message': 'Order processing started'
        })
    }
