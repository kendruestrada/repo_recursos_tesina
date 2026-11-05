from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
import os
import json

logger = Logger()
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')


BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']
table = dynamodb.Table(TABLE_NAME)

@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    try:
        photo_id = event['pathParameters']['photo_id']
        logger.info(f"Iniciando borrado para foto_id: {photo_id}")
        
        # 1. Obtener metadata de DynamoDB
        response = table.get_item(Key={'photo_id': photo_id})
        
        if 'Item' not in response:
            logger.warning("Foto no encontrada en DynamoDB")
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Foto no encontrada'})
            }
        
        photo = response['Item']
        s3_key = photo['s3_key']
        
        logger.info(f"Metadata encontrada. S3 Key: {s3_key}")
        
        s3_prefix = s3_key.rsplit('/', 1)[0] + '/'
        
        
        # 🐛 Lista TODOS los objetos bajo ese prefix
        objects_to_delete = []
        paginator = s3.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=s3_prefix):
            if 'Contents' in page:
                objects_to_delete.extend([{'Key': obj['Key']} for obj in page['Contents']])
        
        logger.info(f"⚠️ A punto de eliminar {len(objects_to_delete)} objetos!")
        
        if objects_to_delete:
            s3.delete_objects(
                Bucket=BUCKET_NAME,
                Delete={'Objects': objects_to_delete}
            )
            logger.info("Objetos eliminados de S3 exitosamente")
        
        # 2. Eliminar metadata de DynamoDB (solo la foto solicitada)
        table.delete_item(Key={'photo_id': photo_id})
        logger.info("Metadata eliminada de DynamoDB")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'mensaje': 'Foto eliminada',
                'photo_id': photo_id,
                'eliminados_de_s3': len(objects_to_delete),
                'advertencia': f'Se eliminaron {len(objects_to_delete)} objetos de S3'
            })
        }
        
    except Exception as e:
        logger.exception("Error procesando eliminación")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }