import os
import json
import boto3
from decimal import Decimal
from aws_lambda_powertools import Logger, Tracer, Metrics
from boto3.dynamodb.conditions import Key

# Inicialización de Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


# Configuración de DynamoDB
TABLE_NAME = os.environ.get("TABLE_NAME", "Products")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
@logger.inject_lambda_context
def lambda_handler(event, context):
    query_params = event.get("queryStringParameters") or {}
    category = query_params.get("category", "electronics")

    try:
        page = int(query_params.get("page", 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1

    try:
        limit = int(query_params.get("limit", 20))
    except (ValueError, TypeError):
        limit = 20

    logger.info(
        f"Iniciando búsqueda para la categoría: {category}, pagina: {page} con limite {limit}"
    )

    try:
        fetch_limit = limit

        query_kwargs = {
            "KeyConditionExpression": Key("category_id").eq(category),
            "Limit": fetch_limit,
        }

        all_items = []

        while True:
            response = table.query(**query_kwargs)
            all_items.extend(response.get("Items", []))

            if len(all_items) >= fetch_limit:
                break

            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break

            query_kwargs["ExclusiveStartKey"] = last_key
            query_kwargs["Limit"] = fetch_limit - len(all_items)

        items = all_items[:fetch_limit]

        safe_items = []
        for i in items:
            safe_item = i.copy()
            if "data" in safe_item:
                safe_item["data"] = "(payload hidden)"
            safe_items.append(safe_item)

        result = {
            "count": len(items),
            "category": category,
            "items": safe_items,
            "page": page,
        }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result, cls=DecimalEncoder),
        }

    except Exception as e:
        logger.error(f"Error consultando DynamoDB: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Error de base de datos", "details": str(e)}),
        }
