import json
import os
import boto3
import redis
from aws_lambda_powertools import Logger

logger = Logger()

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]
REDIS_ENDPOINT = os.environ["REDIS_ENDPOINT"]
REDIS_PORT = int(os.environ["REDIS_PORT"])
CACHE_TTL = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))

redis_client = redis.Redis(host=REDIS_ENDPOINT, port=REDIS_PORT, decode_responses=True)


@logger.inject_lambda_context
def lambda_handler(event, context):
    product_id = (event.get("pathParameters") or {}).get("productId")

    if not product_id:
        return {"statusCode": 400, "body": json.dumps({"error": "productId requerido"})}

    try:
        cache_key = f"price:{product_id}"
        cached_price = redis_client.get(cache_key)

        if cached_price:
            price = float(cached_price)
            logger.info(
                "Precio obtenido desde cache",
                productId=product_id,
                precio=price,
                origen="cache",
            )
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"productId": product_id, "price": price, "source": "cache"}
                ),
            }

        logger.info(
            "Precio no encontrado en cache, consultando base de datos",
            productId=product_id,
        )

        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={"productId": product_id})
        item = response.get("Item")

        if not item:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Producto no encontrado"}),
            }

        price = float(item.get("price", 0))
        logger.info(
            "Precio obtenido desde base de datos",
            productId=product_id,
            precio=price,
            origen="database",
        )

        redis_client.setex(cache_key, CACHE_TTL, str(price))
        logger.info(
            "Precio guardado en cache",
            productId=product_id,
            precio=price,
            ttlSegundos=CACHE_TTL,
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"productId": product_id, "price": price, "source": "database"}
            ),
        }

    except Exception as e:
        logger.error("Error al obtener precio", error=str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Error interno del servidor"}),
        }
