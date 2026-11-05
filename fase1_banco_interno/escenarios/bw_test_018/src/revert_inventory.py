import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['TABLE_NAME']

def handler(event, context):
    order_id = event['order_id']
    
    print(f"🔄 [RevertInventory] Compensating inventory for order {order_id}")
    print(f"🔄 Restoring stock...")
    
    
    table = dynamodb.Table(TABLE_NAME)
    table.update_item(
        Key={'order_id': order_id},
        UpdateExpression='SET inventory_updated = :updated',
        ExpressionAttributeValues={
            ':updated': False
        }
    )
    
    print(f"✅ Inventory compensation successful")
    
    return {
        'status': 'success',
        'inventory_reverted': True
    }
