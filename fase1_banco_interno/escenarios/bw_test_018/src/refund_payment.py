import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['TABLE_NAME']

def handler(event, context):
    order_id = event['order_id']
    payment_id = event.get('paymentResult', {}).get('payment_id', 'unknown')
    
    print(f"💸 [RefundPayment] Attempting to refund payment for order {order_id}")
    print(f"💸 Payment ID: {payment_id}")
    print(f"💸 Calling Payment Gateway API...")
    
    
    print(f"❌ Payment Gateway returned: 429 Too Many Requests")
    print(f"❌ Rate limit exceeded - cannot process refund")
    print(f"⚠️  CRITICAL: Payment was charged but refund FAILED!")
    
    
    raise Exception("Payment Gateway Error: 429 Too Many Requests - Rate limit exceeded")
