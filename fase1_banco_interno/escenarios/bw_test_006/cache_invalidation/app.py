import os
import redis
import requests
from aws_lambda_powertools import Logger

logger = Logger()

REDIS_ENDPOINT = os.environ["REDIS_ENDPOINT"]
REDIS_PORT = int(os.environ["REDIS_PORT"])
PROCESSOR_API_URL = os.environ["PROCESSOR_API_URL"]

redis_client = redis.Redis(host=REDIS_ENDPOINT, port=REDIS_PORT, decode_responses=True)


@logger.inject_lambda_context
def lambda_handler(event, context):
    for record in event.get("Records", []):
        event_name = record.get("eventName")

        if event_name not in ["MODIFY", "REMOVE"]:
            continue

        keys = record.get("dynamodb", {}).get("Keys", {})
        product_id = keys.get("productId", {}).get("S")

        if not product_id:
            continue

        old_image = record.get("dynamodb", {}).get("OldImage", {})
        new_image = record.get("dynamodb", {}).get("NewImage", {})
        old_price = old_image.get("price", {}).get("N")
        new_price = new_image.get("price", {}).get("N")

        logger.info(
            "Cambio de precio detectado en DynamoDB Stream",
            productId=product_id,
            precioAnterior=old_price,
            precioNuevo=new_price,
        )

        try:
            response = requests.get(PROCESSOR_API_URL)
            logger.info(
                "Llamada a API externa completada", statusCode=response.status_code
            )
        except Exception as e:
            logger.error("Error llamando a API externa", error=str(e))

        cache_key = f"price:{product_id}"
        deleted = redis_client.delete(cache_key)

        logger.info(
            "Cache invalidado", productId=product_id, cacheEliminado=bool(deleted)
        )

    return {"statusCode": 200, "processed": len(event.get("Records", []))}
