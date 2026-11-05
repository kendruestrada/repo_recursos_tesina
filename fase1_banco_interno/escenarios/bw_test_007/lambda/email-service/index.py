import json
import os
import time
import boto3
import random
import urllib.request
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# Circuit Breaker State
class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=5):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def debug(self):
        print(f"self.failure_threshold: {self.failure_threshold}")
        print(f"self.recovery_timeout:  {self.recovery_timeout}")
        print(f"self.failure_count:     {self.failure_count}")
        print(f"self.last_failure_time: {self.last_failure_time}")
        print(f"self.state:             {self.state}")
        print(f"Time:        {time.time()}")

    def call(self, func, *args, **kwargs):
        self.debug()
        if self.state == "OPEN":
            if time.time() < self.last_failure_time + self.recovery_timeout:
                self.state = "HALF-OPEN"
                print("Transition to HALF-OPEN state.")
            else:
                raise Exception("Circuit breaker is OPEN - all requests blocked")

        try:
            result = func(*args, **kwargs)

            if self.state == "HALF-OPEN":
                print("Transition to CLOSED state (success in half-open).")
                self.state = "CLOSED"
                self.failure_count = 0

            if self.state == "CLOSED":
                self.failure_count = 0

            return result

        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                if self.state != "OPEN":
                    print(f"Transition to OPEN state (after {self.failure_count} failures)")
                self.state = "OPEN"
                self.last_failure_time = time.time()
            raise e

circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=5)

def send_email_via_ses(order_id, email, notification_type="EMAIL"):
    
    if notification_type == 'NONE':
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Internal process logged. No email sent.', 'orderId': order_id})
        }

    is_healthy = external_status_check()

    if not is_healthy:
        error_response = {
            'Error': {
                'Code': 'ServiceUnavailable', 
                'Message': 'The request has failed due to a temporary failure of the service.'
            }
        }
        raise ClientError(error_response, 'SendEmail')

    ses_client = boto3.client('ses')
    
    try:
        response = ses_client.send_email(
            Source=os.environ.get('SENDER_EMAIL', 'no-reply@example.com'),
            Destination={'ToAddresses': [email]},
            Message={
                'Subject': {'Data': f'Order Confirmation - {order_id}'},
                'Body': {'Text': {'Data': f'Your order {order_id} has been processed successfully.'}}
            }
        )
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'MessageRejected':
            return {'statusCode': 200, 'body': json.dumps({'message': 'Accepted'})}
        raise e

def lambda_handler(event, context):
    try:
        print(f"EmailService received event: {json.dumps(event)}")

        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        order_id = body.get('orderId')
        email = body.get('email')
        notification_type = body.get('notificationType', 'EMAIL')

        if not order_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing orderId'})
            }

        try:
            result = circuit_breaker.call(send_email_via_ses, order_id, email, notification_type)
            
            if isinstance(result, dict) and 'statusCode' in result:
                return result

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Email sent successfully',
                    'orderId': order_id,
                    'email': email,
                    'circuitBreakerState': circuit_breaker.state,
                    'failureCount': circuit_breaker.failure_count
                })
            }
        except Exception as cb_error:
            error_message = str(cb_error)
            status_code = 503 if "Circuit breaker is OPEN" in error_message else 504

            return {
                'statusCode': status_code,
                'body': json.dumps({
                    'error': error_message,
                    'orderId': order_id,
                    'email': email,
                    'circuitBreakerState': circuit_breaker.state,
                    'failureCount': circuit_breaker.failure_count
                })
            }

    except Exception as e:
        print(f"Error in EmailService: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def external_status_check():
    url = os.environ.get('STATUS_CHECK_URL')
    try:
        print(f"Requesting external status check...")
        with urllib.request.urlopen(url, timeout=2) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"External check unavailable: {str(e)}")  
        return False