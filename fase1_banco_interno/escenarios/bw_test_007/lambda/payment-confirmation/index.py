import json
import os
import boto3

lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    try:
        print(f"PaymentConfirmation received event: {json.dumps(event)}")

        # Extract orderId and email from API Gateway event
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        order_id = body.get('orderId')
        email = body.get('email')

        if not order_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'Missing orderId in request body'
                })
            }

        # Confirm payment
        print(f"Confirming payment for order: {order_id}, email: {email}")

        # Call OrderProcessing Lambda
        order_processing_arn = os.environ.get('ORDER_PROCESSING_FUNCTION_NAME')
        if not order_processing_arn:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'OrderProcessing function not configured'
                })
            }

        # Invoke OrderProcessing
        order_payload = {
            'body': json.dumps({
                'orderId': order_id,
                'email': email
            })
        }

        print(f"Invoking OrderProcessing with payload: {json.dumps(order_payload)}")

        response = lambda_client.invoke(
            FunctionName=order_processing_arn,
            InvocationType='RequestResponse',
            Payload=json.dumps(order_payload)
        )

        order_response = json.loads(response['Payload'].read())
        order_status_code = order_response.get('statusCode', 500)

        print(f"OrderProcessing response: {json.dumps(order_response)}")

        # Return the response from OrderProcessing
        return {
            'statusCode': order_status_code,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': order_response.get('body', json.dumps({
                'message': 'Payment confirmed',
                'orderId': order_id
            }))
        }

    except Exception as e:
        print(f"Error in PaymentConfirmation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }
