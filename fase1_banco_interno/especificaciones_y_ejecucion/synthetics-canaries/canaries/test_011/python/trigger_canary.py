import os
import json
import urllib3
import boto3
import time
from datetime import datetime, timedelta
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):

    logger.info("🔍 Starting Canary Test 011 (Duplicate Email Detection via SQS)...")
    
    api_url = os.environ.get('API_ENDPOINT')
    lambda_function_name = os.environ.get('TEST_011_EMAIL_FUNCTION_NAME')

    if not api_url or not lambda_function_name:
        logger.error("❌ Error: Missing required environment variables")
        raise Exception("Configuration error: API_ENDPOINT or TEST_011_EMAIL_FUNCTION_NAME not set")
        
    logger.info(f"📍 API Endpoint: {api_url}")
    logger.info(f"📍 Lambda Function: {lambda_function_name}")

    payload = {
        "customer_email": "canary_bot@test.com",
        "items": ["Test Item A", "Test Item B"],
        "amount": 100
    }
    
    encoded_body = json.dumps(payload).encode('utf-8')

    http = urllib3.PoolManager()
    cloudwatch = boto3.client('cloudwatch')
    
    try:
        logger.info("🚀 Step 1: Triggering order creation...")
        
        response = http.request(
            'POST',
            api_url,
            body=encoded_body,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'AWS-Synthetics-Canary/Test-011'
            },
            timeout=10.0
        )
        
        logger.info(f"📡 Order API Response: {response.status}")
        
        if response.status not in [200, 201]:
            error_message = f"❌ API Error: {response.status}"
            logger.error(error_message)
            raise Exception(error_message)
            
        response_body = json.loads(response.data.decode('utf-8'))
        order_id = response_body.get('order_id')
        logger.info(f"✅ Order created: {order_id}")
        
        # Step 2: Wait for SQS reprocessing + CloudWatch Metrics delay
        # SQS visibility timeout is 10s, 5 invocations = ~50s
        # CloudWatch Metrics have delay. Wait 2 minutes to ensure consistent data.
        wait_time = 120
        logger.info(f"⏳ Step 2: Waiting {wait_time}s for SQS message reprocessing and CloudWatch Metrics...")
        time.sleep(wait_time)
        
        # Step 3: Query CloudWatch Metrics for Lambda invocations
        logger.info("🔍 Step 3: Querying CloudWatch Metrics for Lambda invocations...")
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(seconds=300)  # Look back 5 minutes
        
        metric_response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Invocations',
            Dimensions=[
                {'Name': 'FunctionName', 'Value': lambda_function_name}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=60,
            Statistics=['Sum']
        )
        
        # Step 4: Verify bug (multiple invocations = message reprocessing)
        if not metric_response['Datapoints']:
            logger.warning("⚠️ No metric data found. Bug may not have triggered yet.")
            raise Exception("No invocation metrics found for EmailSender Lambda")
        
        # Sum all datapoints (in case metrics are split across minutes)
        invocation_count = sum(dp['Sum'] for dp in metric_response['Datapoints'])
        invocation_count = int(invocation_count)
        logger.info(f"📊 EmailSender Lambda Invocations: {invocation_count}")
        
        # Expected: >= 3 invocations (message being reprocessed due to DeleteMessage failures)
        if invocation_count >= 3:
            logger.info(f"🎯 BUG DETECTED!")
            logger.info(f"   ├─ Lambda invoked {invocation_count} times")
            logger.info(f"   ├─ Expected: 1 invocation")
            logger.info(f"   └─ SQS message is being reprocessed (DeleteMessage failing)")
            logger.info(f"✅ CANARY PASSED: Duplicate email bug successfully detected")
            return {"status": "success", "bug_detected": True, "invocations": invocation_count}
        else:
            logger.warning(f"⚠️ Bug NOT detected")
            logger.warning(f"   ├─ Lambda invoked only {invocation_count} time(s)")
            logger.warning(f"   ├─ Expected: >= 3 invocations")
            logger.warning(f"   └─ SQS DeleteMessage may be working correctly")
            raise Exception(f"Bug not reproduced. Only {invocation_count} invocation(s) detected")
            
    except Exception as e:
        logger.error(f"❌ Canary Error: {str(e)}")
        raise e