import json
import os
import boto3
from aws_lambda_powertools import Logger

logger = Logger()

lambda_client = boto3.client("lambda")
INVENTORY_FUNCTION_NAME = os.environ["INVENTORY_FUNCTION_NAME"]


@logger.inject_lambda_context
def lambda_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    product_id = body.get("productId")
    price = body.get("price")
    quantity = body.get("quantity", 1)

    if not product_id or price is None:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "productId y price son requeridos"}),
        }

    try:
        response = lambda_client.invoke(
            FunctionName=INVENTORY_FUNCTION_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps(
                {"productId": product_id, "price": price, "quantity": quantity}
            ),
        )

        validation = json.loads(response["Payload"].read())

        if not validation.get("valid"):
            if validation.get("actualPrice") is not None:
                logger.error(
                    "Checkout rechazado por inconsistencia de precio",
                    productId=product_id,
                    precioMostradoAlUsuario=price,
                    precioRealEnDB=validation.get("actualPrice"),
                )

            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "success": False,
                        "error": validation.get("error"),
                        "details": validation,
                    }
                ),
            }

        logger.info(
            "Checkout completado exitosamente",
            productId=product_id,
            precio=validation.get("price"),
            cantidad=quantity,
            total=validation.get("price") * quantity,
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "success": True,
                    "productId": product_id,
                    "price": validation.get("price"),
                    "quantity": quantity,
                    "totalAmount": validation.get("price") * quantity,
                }
            ),
        }

    except Exception as e:
        logger.error("Error al procesar checkout", error=str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Error interno del servidor"}),
        }
