import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['TABLE_NAME']

def handler(event, context):
    order_id = event['order_id']
    
    print(f"📦 [UpdateInventory] Updating inventory for order {order_id}")
    print(f"📦 Reducing stock...")
    print(f"✅ Inventory updated successfully")
    
    table = dynamodb.Table(TABLE_NAME)
    table.update_item(
        Key={'order_id': order_id},
        UpdateExpression='SET #status = :status, inventory_updated = :updated',
        ExpressionAttributeNames={
            '#status': 'status'
        },
        ExpressionAttributeValues={
            ':status': 'completed',  
            ':updated': True
        }
    )
    
    print(f"⚠️  Order status set to 'completed' (this is the bug!)")
    
    return {
        'status': 'success',
        'inventory_updated': True
    }
