import json
import os
from datetime import datetime
import boto3

lambda_client = boto3.client("lambda")
RISK_LAMBDA_NAME = os.environ["RISK_LAMBDA_NAME"]
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def lambda_handler(event, context):
    print("lambda CreditEvaluation")
    body = json.loads(event.get("body", "{}"))
    credit_id = body.get("credit_id")
    print("body:", body)

    try:
        print("Se guarda solicitud en dynamodb con status=pending")
        table.update_item(
            Key={"credit_id": str(credit_id)},
            UpdateExpression="SET #st = :status, updated_at = :now",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":status": "pending",
                ":now": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            },
        )
        print(f"Registro {credit_id} guardado con estado=pending")

        # invoca a RiskAnalysis para consultar a la tabla
        response = lambda_client.invoke(
            FunctionName=RISK_LAMBDA_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps({"credit_id": credit_id}),
        )

        payload = json.loads(response["Payload"].read())
        status_code = payload.get("statusCode", 500)
        print("status_code: ", status_code)

        if status_code != 200:
            print("No se pudo actualizar estado")

        return {"statusCode": status_code, "body": payload.get("body", "{}")}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
