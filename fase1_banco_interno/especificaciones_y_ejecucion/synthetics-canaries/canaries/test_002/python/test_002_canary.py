import os
import json
import urllib3
import uuid
import boto3
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    logger.info("Iniciando Canary Test 002 (Inconsistencia de Pagos)...")
    
    api_url = os.environ.get('API_ENDPOINT')
    dynamodb_table_name = os.environ.get('DYNAMODB_TABLE_NAME')
    if not api_url:
        logger.error("Error: API_ENDPOINT no configurado")
        raise Exception("Falta configuración de URL")
    if not dynamodb_table_name:
        logger.error("Error: DYNAMODB_TABLE_NAME no configurado")
        raise Exception("Falta configuración de DYNAMODB_TABLE_NAME")

    # Generamos una TRX única para el monitoreo
    transaction_id = f"TRX_CANARY_{uuid.uuid4().hex[:6]}"
    full_url = f"{api_url}?transaction_id={transaction_id}"
    
    http = urllib3.PoolManager()
    
    try:
        logger.info(f"Ejecutando llamada a: {full_url}")
        
        response = http.request(
            'GET', 
            full_url
        )
        
        data = json.loads(response.data.decode('utf-8'))
        db_status = data.get('db_status')

        logger.info(f"📡 Respuesta: DB={db_status}")

        # Comprobar en dynamodb si existe el registro
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(dynamodb_table_name)
        response = table.get_item(
            Key={
                'transaction_id': transaction_id
            }
        )
        item = response.get('Item')

        if item:
            logger.info(f"✅ Registro encontrado en DynamoDB: {item}")
        else:
            logger.error(f"❌ Registro NO encontrado en DynamoDB")
            raise Exception("Registro no encontrado en DynamoDB")

        logger.info("Ejecución finalizada.")

    except Exception as e:
        logger.error(f"Error Crítico en ejecución: {str(e)}")
        raise e