import os
import json
import boto3
import time
import urllib3
from aws_synthetics.common import synthetics_logger

def handler(event, context):
    # 1. Configuration
    api_endpoint = os.environ.get("TEST_014_API_ENDPOINT")
    table_name = os.environ.get("TEST_014_USER_POINTS_TABLE_NAME")
    
    if not api_endpoint or not table_name:
        raise ValueError("❌ Missing environment variables: TEST_014_API_ENDPOINT or TEST_014_USER_POINTS_TABLE_NAME")

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    http = urllib3.PoolManager()
    
    user_id = "user_test_14"
    initial_points = 100
    points_to_add = 50
    
    synthetics_logger.info(f"Starting Test 014: Idempotency Check on {api_endpoint}")

    # 2. Setup: Reset User State
    synthetics_logger.info(f"Resetting user {user_id} to {initial_points} points")
    table.put_item(
        Item={
            'user_id': user_id,
            'points': initial_points
        }
    )
    
    # 3. Attack: Simulate Duplicate Delivery via API
    # We send the same payload twice via HTTP POST
    
    payload = {
        "detail": {
            "user_id": user_id,
            "amount": 500,
            "points_earned": points_to_add
        }
    }
    
    encoded_payload = json.dumps(payload).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    
    synthetics_logger.info("Sending Request 1 (Attempt 1)")
    response1 = http.request(
        'POST',
        api_endpoint,
        body=encoded_payload,
        headers=headers
    )
    synthetics_logger.info(f"Response 1 Status: {response1.status}")

    
    synthetics_logger.info("Sending Request 2 (Attempt 2 - Duplicate)")
    response2 = http.request(
        'POST',
        api_endpoint,
        body=encoded_payload,
        headers=headers
    )
    synthetics_logger.info(f"Response 2 Status: {response2.status}")
    
    # Add a small delay to ensure DynamoDB writes complete
    time.sleep(2)
    
    # 4. Verification
    response = table.get_item(Key={'user_id': user_id})
    item = response.get('Item', {})
    final_points = int(item.get('points', 0))
    
    expected_if_correct = initial_points + points_to_add # 150
    expected_if_bug = initial_points + points_to_add + points_to_add # 200
    
    synthetics_logger.info(f"Final Points: {final_points}")
    
    if final_points == expected_if_bug:
        synthetics_logger.info("✅ SUCCESS: Bug reproduced! Points are 200 (Double counted).")
        return "Test 014 Passed: Idempotency failure detected via API."
    elif final_points == expected_if_correct:
         # Note: If the API Gateway handles requests sequentially and slow enough, logic might work if not racy.
         # But the code is intentionally non-idempotent logic.
        raise Exception(f"❌ FAILURE: Bug NOT reproduced. Points are {final_points}. Logic might be idempotent?")
    else:
        raise Exception(f"❓ INCONCLUSIVE: Points are {final_points}. Expected 200 (Bug) or 150 (Correct).")
