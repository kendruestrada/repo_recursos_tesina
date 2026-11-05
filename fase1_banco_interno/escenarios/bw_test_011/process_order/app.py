import json
import os
import boto3
import uuid

sqs = boto3.client("sqs")
QUEUE_URL = os.environ["QUEUE_URL"]


def lambda_handler(event, context):
    order_id = str(uuid.uuid4())

    body = json.loads(event["body"])

    if "order_id" in body:
        order_id = body["order_id"]

    if "customer_email" in body:
        customer_email = body["customer_email"]

    if "amount" in body:
        amount = body["amount"]

    message_body = {
        "order_id": order_id,
        "customer_email": customer_email,
        "amount": amount,
    }

    response = sqs.send_message(
        QueueUrl=QUEUE_URL, MessageBody=json.dumps(message_body)
    )

    print(f"Orden procesada. Mensaje enviado a SQS ID: {response['MessageId']}")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Orden enviada", "order_id": order_id}),
    }
