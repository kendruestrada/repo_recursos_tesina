import os
import json
import boto3
import time
import urllib3
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    api_endpoint = os.environ.get('API_ENDPOINT')
    table_name = "test-005-Credit"
    # Generamos un ID único para no colisionar con ejecuciones anteriores
    unique_credit_id = f"canary-credit-{int(time.time())}"
    
    http = urllib3.PoolManager()
    dynamodb = boto3.client('dynamodb')

    logger.info(f'Paso 1: Disparando solicitud de crédito {unique_credit_id}...')
    
    try:
        # La Lambda A tiene un timeout de 10s. Esperamos el fallo.
        payload = json.dumps({"credit_id": unique_credit_id})
        response = http.request(
            'POST', 
            api_endpoint, 
            body=payload,
            headers={'Content-Type': 'application/json'},
            timeout=15.0 # Un poco más que el timeout de la Lambda
        )
        logger.info(f"La API respondió con status: {response.status}")
    except Exception as e:
        logger.info(f"La petición falló o dio timeout (comportamiento esperado): {str(e)}")

    # Paso 2: Tiempo de espera para que los reintentos internos terminen
    logger.info("Paso 2: Esperando 20s para confirmar la inconsistencia en DynamoDB...")
    time.sleep(20)

    # Paso 3: Verificación del estado "Zombie"
    logger.info(f"Paso 3: Consultando tabla {table_name}...")
    res = dynamodb.get_item(
        TableName=table_name, 
        Key={'credit_id': {'S': unique_credit_id}}
    )
    
    item = res.get('Item', {})
    actual_status = item.get('status', {}).get('S', 'NOT_FOUND')
    logger.info(f"Estado detectado en DB: {actual_status}")

    # Paso 4: Veredicto del Benchmark
    # El éxito del benchmark es que el estado se quede en 'pending'
    if actual_status == "pending":
        logger.info("BUG CONFIRMADO: El registro quedó huérfano en estado 'pending'.")
        
        # Limpieza para mantener la tabla sana
        dynamodb.delete_item(TableName=table_name, Key={'credit_id': {'S': unique_credit_id}})
        return {"body": "Test 005: Inconsistency verified successfully"}
    else:
        # Si el estado es otro, el bug no se reprodujo correctamente
        error_msg = f"FALLO: Se esperaba 'pending' pero se encontró '{actual_status}'."
        logger.error(error_msg)
        raise Exception(error_msg)