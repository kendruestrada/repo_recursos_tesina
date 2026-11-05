import os
import json
import time
import boto3
import urllib3
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    logger.info("🔍 Starting Canary Test 018 (Saga Compensation Failure Detection)...")
    
    api_endpoint = os.environ.get('TEST_018_API_ENDPOINT')
    table_name = os.environ.get('TEST_018_TABLE_NAME')
    state_machine_arn = os.environ.get('TEST_018_STATE_MACHINE_ARN')
    
    if not all([api_endpoint, table_name, state_machine_arn]):
        logger.error("❌ Missing required environment variables")
        raise Exception("Configuration error: missing environment variables")
    
    logger.info(f"📍 API Endpoint: {api_endpoint}")
    logger.info(f"📍 DynamoDB Table: {table_name}")
    logger.info(f"📍 State Machine: {state_machine_arn}")
    
    # Step 1: Trigger an order via API
    logger.info("🚀 Step 1: Triggering order creation...")
    http = urllib3.PoolManager()
    
    payload = {
        "customer_email": "canary@test.com",
        "amount": 99.99
    }
    
    response = http.request(
        'POST',
        api_endpoint,
        body=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        timeout=10.0
    )
    
    if response.status not in [200, 201]:
        logger.error(f"❌ API call failed with status {response.status}")
        raise Exception(f"API returned {response.status}")
    
    response_data = json.loads(response.data.decode('utf-8'))
    order_id = response_data['order_id']
    execution_arn = response_data['execution_arn']
    
    logger.info(f"✅ Order created: {order_id}")
    logger.info(f"✅ Execution ARN: {execution_arn}")
    
    # Step 2: Wait for Step Functions execution to complete
    logger.info("⏳ Step 2: Waiting for Step Functions execution to complete...")
    sfn_client = boto3.client('stepfunctions')
    
    max_wait = 60  # Wait up to 60 seconds
    wait_interval = 2
    elapsed = 0
    execution_status = None
    
    while elapsed < max_wait:
        time.sleep(wait_interval)
        elapsed += wait_interval
        
        exec_response = sfn_client.describe_execution(executionArn=execution_arn)
        execution_status = exec_response['status']
        
        logger.info(f"⏱️  Execution status: {execution_status} (waited {elapsed}s)")
        
        if execution_status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
            break
    
    if execution_status not in ['SUCCEEDED', 'FAILED']:
        logger.error(f"❌ Execution did not complete in time: {execution_status}")
        raise Exception(f"Execution timeout or unexpected status: {execution_status}")
    
    logger.info(f"✅ Execution completed with status: {execution_status}")
    
    # Step 3: Check DynamoDB for order status
    logger.info("🔍 Step 3: Checking order status in DynamoDB...")
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    db_response = table.get_item(Key={'order_id': order_id})
    
    if 'Item' not in db_response:
        logger.error(f"❌ Order {order_id} not found in DynamoDB")
        raise Exception("Order not found in database")
    
    order = db_response['Item']
    order_status = order.get('status', 'unknown')
    payment_status = order.get('payment_status', 'unknown')
    
    logger.info(f"📊 Order Status: {order_status}")
    logger.info(f"📊 Payment Status: {payment_status}")
    
    # Step 4: Verify the bug
    logger.info("🧪 Step 4: Verifying inconsistent state (the bug)...")
    
    # Expected bug scenario:
    # - Step Functions execution: FAILED (because warehouse and refund failed)
    # - Order status in DB: "completed" (BUG! Should be "failed" or "cancelled")
    # - Payment status: "charged" (BUG! Should be "refunded" or at least not charged)
    
    bug_detected = False
    
    if execution_status == 'FAILED' and order_status == 'completed':
        logger.info("🎯 BUG DETECTED!")
        logger.info("   ├─ Step Functions: FAILED")
        logger.info("   ├─ Order Status: completed (WRONG!)")
        logger.info("   └─ This is the inconsistent state we're looking for")
        bug_detected = True
    else:
        logger.warning("⚠️  Bug NOT detected")
        logger.warning(f"   ├─ Step Functions: {execution_status}")
        logger.warning(f"   ├─ Order Status: {order_status}")
        logger.warning("   └─ Expected: FAILED execution + 'completed' status")
    
    # Additional verification: Check if payment was charged but not refunded
    if payment_status == 'charged':
        logger.info("💳 Payment Status: charged (customer was charged)")
        logger.info("⚠️  CRITICAL: Payment charged but saga failed!")
    
    # For this canary, SUCCESS means we detected the bug
    if bug_detected:
        logger.info("✅ CANARY PASSED: Successfully detected the Saga compensation failure bug")
        return {"status": "success", "bug_detected": True}
    else:
        logger.error("❌ CANARY FAILED: Bug was not reproduced")
        raise Exception("Expected bug scenario not detected")
