import json
import os
import time
import boto3
from decimal import Decimal
from aws_lambda_powertools import Logger

logger = Logger()

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]


@logger.inject_lambda_context
def lambda_handler(event, context):
    product_id = (event.get("pathParameters") or {}).get("productId")
    body = json.loads(event.get("body") or "{}")
    new_price = body.get("price")

    if not product_id or new_price is None:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "productId y price son requeridos"}),
        }

    try:
        table = dynamodb.Table(TABLE_NAME)
        new_price_decimal = Decimal(str(new_price))

        table.update_item(
            Key={"productId": product_id},
            UpdateExpression="SET price = :p, updatedAt = :u",
            ExpressionAttributeValues={":p": new_price_decimal, ":u": int(time.time())},
            ReturnValues="ALL_NEW",
        )

        logger.warning(
            "Precio actualizado en DB",
            productId=product_id,
            nuevoPrecio=float(new_price_decimal),
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "success": True,
                    "productId": product_id,
                    "newPrice": float(new_price_decimal),
                },
                default=str,
            ),
        }

    except Exception as e:
        logger.error("Error al actualizar precio", error=str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Error interno del servidor"}),
        }
