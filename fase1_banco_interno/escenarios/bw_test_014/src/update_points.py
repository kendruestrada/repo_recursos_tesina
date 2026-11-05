import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME')
table = dynamodb.Table(table_name)

def handler(event, context):
    print("Received event:", json.dumps(event))
    
    if 'body' in event:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            
            if 'detail' in body:
                detail = body['detail']
            else:
                
                detail = body
        except Exception as e:
            print(f"Error parsing body: {e}")
            return {'statusCode': 400, 'body': 'Invalid JSON body'}
            
    
    elif 'detail' in event:
        detail = event['detail']
    else:
        
        detail = event

    user_id = detail.get('user_id')
    points_earned = detail.get('points_earned', 0)
    
    if not user_id:
        print("Error: No user_id found in event")
        return {
            'statusCode': 400,
            'body': json.dumps("Missing user_id")
        }
    
    print(f"Processing points update for user {user_id}: +{points_earned}")
    

    response = table.get_item(Key={'user_id': user_id})
    item = response.get('Item', {})
    current_points = int(item.get('points', 0))
    
    print(f"Current points for {user_id}: {current_points}")
    
    new_total = current_points + points_earned

    table.put_item(
        Item={
            'user_id': user_id,
            'points': new_total
        }
    )
    
    print(f"Updated points for {user_id}: {new_total}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            "message": f"Updated user {user_id} to {new_total} points",
            "user_id": user_id,
            "new_points": new_total
        })
    }
