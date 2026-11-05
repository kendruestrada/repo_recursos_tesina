import json
import os
import boto3
import uuid

events = boto3.client('events')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME', 'default')

def handler(event, context):
    # Retrieve input or use defaults
    body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event
    
    user_id = body.get('user_id', 'user_12345')
    amount = body.get('amount', 100)
    points = body.get('points_earned', 10)
    
    detail = {
        "user_id": user_id,
        "amount": amount,
        "points_earned": points
    }
    
    print(f"Emitting PurchaseCompleted event for {user_id}")
    
    response = events.put_events(
        Entries=[
            {
                'Source': 'com.bugwizard.store',
                'DetailType': 'PurchaseCompleted',
                'Detail': json.dumps(detail),
                'EventBusName': EVENT_BUS_NAME
            }
        ]
    )
    
    print("Event emitted:", response)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            "message": "Purchase processed and event emitted",
            "detail": detail,
            "response": response
        })
    }
