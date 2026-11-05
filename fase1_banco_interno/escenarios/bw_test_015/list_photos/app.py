from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
import os
import json

logger = Logger()
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

BUCKET_NAME = os.environ["BUCKET_NAME"]
TABLE_NAME = os.environ["TABLE_NAME"]
table = dynamodb.Table(TABLE_NAME)


@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    """
    Lista fotos de un usuario y verifica inconsistencias entre DynamoDB y S3
    """
    try:
        user_id = event["pathParameters"]["user_id"]
        logger.info(f"Listando fotos para usuario: {user_id}")

        # 1. Obtener metadata de DynamoDB
        response = table.query(
            IndexName="user_id-index",
            KeyConditionExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id},
        )

        photos_in_db = response.get("Items", [])
        logger.info(f"Encontradas {len(photos_in_db)} entradas en DynamoDB")

        # 2. Listar objetos en S3
        s3_prefix = f"users/{user_id}/"
        s3_objects = []

        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=s3_prefix):
            if "Contents" in page:
                s3_objects.extend([obj["Key"] for obj in page["Contents"]])

        logger.info(
            f"Encontrados {len(s3_objects)} objetos en S3 bajo prefix {s3_prefix}"
        )

        # 3. Detectar inconsistencias
        db_keys = {photo["s3_key"] for photo in photos_in_db}
        s3_keys = set(s3_objects)

        orphaned_metadata = db_keys - s3_keys  # En DB pero no en S3
        orphaned_files = s3_keys - db_keys  # En S3 pero no en DB

        if orphaned_metadata:
            logger.error(
                f"{len(orphaned_metadata)} fotos en DB sin archivo en S3 (Perdidas!)"
            )

        if orphaned_files:
            logger.warning(
                f"{len(orphaned_files)} archivos en S3 sin metadata en DB (Huérfanos)"
            )

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(
                {
                    "user_id": user_id,
                    "photos_in_dynamodb": len(photos_in_db),
                    "photos_in_s3": len(s3_objects),
                    "consistent": len(orphaned_metadata) == 0
                    and len(orphaned_files) == 0,
                    "orphaned_metadata": list(orphaned_metadata),
                    "orphaned_files": list(orphaned_files),
                    "photos": photos_in_db,
                },
                indent=2,
            ),
        }

    except Exception as e:
        logger.exception("Error listando fotos")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }
