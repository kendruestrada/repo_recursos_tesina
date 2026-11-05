import json
import os
import boto3
import time
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

internal_cache = {}

def lambda_handler(event, context):
    body = json.loads(event['body'])
    sku = body.get('sku')
    quantity = body.get('quantity')
    user_id = body.get('user_id')
    
    response = table.get_item(Key={'SKU': sku})
    item_db = response.get('Item', {})
    db_stock_antes = int(item_db.get('stock', 0))
    
    if sku not in internal_cache:
        internal_cache[sku] = db_stock_antes
    
    cached_val = internal_cache[sku]
    
    print(f"--- [USUARIO: {user_id}] ---")
    print(f"Estado DB antes: {db_stock_antes}")
    print(f"Visto en Cache: {cached_val}")

    if cached_val >= quantity:
        time.sleep(0.5) 
        
        new_stock = db_stock_antes - quantity
        now = datetime.utcnow().isoformat()
        
        table.put_item(Item={
            'SKU': sku,
            'stock': new_stock,
            'last_updated_by': user_id,
            'updated_at': now
        })
        
        print(f"Estado DB despues: {new_stock}")
        print(f"---------------------------")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Success",
                "detalles": {
                    "cache_visto": cached_val,
                    "db_antes": db_stock_antes,
                    "stock_final": new_stock
                }
            })
        }
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Low stock", "cache_visto": cached_val})
        }