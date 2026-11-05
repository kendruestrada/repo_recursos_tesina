import json
import os
import boto3
import requests

PROCESSOR_URL = os.environ["PROCESSOR_URL"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def lambda_handler(event, context):
    print("lambda RiskAnalysis")
    print("event:", event)
    credit_id = event.get("credit_id")

    if not credit_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "credit_id es requerido"}),
        }

    try:
        response = table.get_item(Key={"credit_id": credit_id})

        print("response dynamodb: ")
        print(response)

        if "Item" not in response:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Crédito no encontrado"}),
            }

        # llama al endpoint processor
        print("Invocando endpoint processor")
        processor_response = requests.get(PROCESSOR_URL)
        print("processor body:", processor_response.text)

        return {"statusCode": 200, "body": json.dumps(response["Item"])}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
