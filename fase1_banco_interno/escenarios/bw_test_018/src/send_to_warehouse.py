import json

def handler(event, context):
    order_id = event['order_id']
    
    print(f"🏭 [SendToWarehouse] Attempting to send order {order_id} to warehouse...")
    print(f"🏭 Calling Warehouse API...")
    

    print(f"❌ Warehouse API returned: 503 Service Unavailable")
    print(f"❌ Warehouse is under maintenance")
    
    raise Exception("Warehouse API Error: 503 Service Unavailable - System under maintenance")
