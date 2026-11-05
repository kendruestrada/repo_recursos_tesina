from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
import os
import json
import uuid
from datetime import datetime

logger = Logger()
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']
table = dynamodb.Table(TABLE_NAME)

@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    """
    Simula subir una foto (crea metadata en DynamoDB y objeto vacío en S3)
    Body: {
        "user_id": "user_123",
        "photo_type": "profile" | "gallery",
        "filename": "photo.jpg"
    }
    """
    try:
        body = json.loads(event.get('body', '{}'))
        user_id = body['user_id']
        photo_type = body.get('photo_type', 'gallery')
        filename = body.get('filename', f'photo_{uuid.uuid4().hex[:8]}.jpg')
        
        logger.info(f"Iniciando subida de foto para usuario: {user_id}, tipo: {photo_type}")
        
        photo_id = f"{photo_type}_{uuid.uuid4().hex[:8]}"
        
        # Construir S3 key
        if photo_type == 'profile':
            s3_key = f"users/{user_id}/profile.jpg"
        else:
            s3_key = f"users/{user_id}/gallery/{filename}"
        
        logger.info(f"Generada S3 Key: {s3_key}")
        
        # Crear objeto vacío en S3 (simulación)
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=b'fake photo content',
            ContentType='image/jpeg'
        )
        logger.info("Objeto creado en S3")
        
        # Guardar metadata en DynamoDB
        table.put_item(Item={
            'photo_id': photo_id,
            'user_id': user_id,
            's3_key': s3_key,
            'type': photo_type,
            'filename': filename,
            'created_at': datetime.utcnow().isoformat()
        })
        logger.info("Metadata guardada en DynamoDB")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Photo uploaded successfully',
                'photo_id': photo_id,
                's3_key': s3_key
            })
        }
        
    except Exception as e:
        logger.exception("Error subiendo foto")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }