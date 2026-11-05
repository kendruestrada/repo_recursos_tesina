import json
import os
import boto3
import uuid

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['TABLE_NAME']

def handler(event, context):
    order_id = event['order_id']
    amount = event['amount']
    
    payment_id = str(uuid.uuid4())
    
    print(f"💳 [ChargePayment] Processing payment for order {order_id}")
    print(f"💳 Amount: ${amount}")
    print(f"💳 Payment ID: {payment_id}")
    print(f"✅ Payment charged successfully")
    
    
    table = dynamodb.Table(TABLE_NAME)
    table.update_item(
        Key={'order_id': order_id},
        UpdateExpression='SET payment_id = :pid, payment_status = :status',
        ExpressionAttributeValues={
            ':pid': payment_id,
            ':status': 'charged'
        }
    )
    
    return {
        'payment_id': payment_id,
        'status': 'success',
        'amount': amount
    }
