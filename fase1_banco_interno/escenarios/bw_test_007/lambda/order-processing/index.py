import json
import os
import boto3

lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    try:
        print(f"OrderProcessing received event: {json.dumps(event)}")

        # Extract orderId and email from event
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        order_id = body.get('orderId')
        email = body.get('email')

        if not order_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing orderId'
                })
            }

        # Process the order
        print(f"Processing order: {order_id} for email: {email}")

        # Call EmailService Lambda
        email_service_arn = os.environ.get('EMAIL_SERVICE_FUNCTION_NAME')
        if not email_service_arn:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'EmailService function not configured'
                })
            }

        # Invoke EmailService
        email_payload = {
            'body': json.dumps({
                'orderId': order_id,
                'email': email
            })
        }

        print(f"Invoking EmailService with payload: {json.dumps(email_payload)}")

        response = lambda_client.invoke(
            FunctionName=email_service_arn,
            InvocationType='RequestResponse',
            Payload=json.dumps(email_payload)
        )

        email_response = json.loads(response['Payload'].read())
        email_status_code = email_response.get('statusCode', 500)

        print(f"EmailService response: {json.dumps(email_response)}")

        if email_status_code != 200:
            # EmailService failed
            return {
                'statusCode': email_status_code,
                'body': json.dumps({
                    'message': 'Order processed but email sending failed',
                    'orderId': order_id,
                    'emailError': json.loads(email_response.get('body', '{}')).get('error', 'Unknown error')
                })
            }

        # Success
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Order processed and email sent successfully',
                'orderId': order_id,
                'email': email
            })
        }

    except Exception as e:
        print(f"Error in OrderProcessing: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }
