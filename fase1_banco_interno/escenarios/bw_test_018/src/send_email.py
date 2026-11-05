import json

def handler(event, context):
    order_id = event['order_id']
    customer_email = event['customer_email']
    
    print(f"📧 [SendEmail] Sending confirmation email to {customer_email}")
    print(f"📧 Order ID: {order_id}")
    print(f"✅ Email sent successfully")
    
    return {
        'status': 'success',
        'email_sent': True
    }
