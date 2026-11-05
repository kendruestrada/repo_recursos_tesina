import os
import json
import boto3
import urllib3
from decimal import Decimal
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    # 1. Configuración desde variables de entorno
    api_endpoint = os.environ.get('API_ENDPOINT')
    policies_table_name = os.environ.get('POLICIES_TABLE')
    risk_table_name = os.environ.get('RISK_TABLE')

    dynamodb = boto3.resource('dynamodb')
    p_table = dynamodb.Table(policies_table_name)
    r_table = dynamodb.Table(risk_table_name)
    http = urllib3.PoolManager()

    logger.info(f"Usando tablas existentes: {policies_table_name} y {risk_table_name}")

    # 2. SEED: Asegurar que los datos específicos del test existan en las tablas
    logger.info("🔧 Sincronizando datos de prueba en DynamoDB...")
    r_table.put_item(Item={'actuarial_age': 0, 'factor': Decimal('0.0')})
    r_table.put_item(Item={'actuarial_age': 35, 'factor': Decimal('1.2')})

    # Póliza con el BUG (Infante edad 0)
    p_table.put_item(Item={
        'policy_id': '144534',
        'holder_name': 'Juan Perez',
        'holder_age': 35,
        'status': 'active',
        'dependents': [{'name': 'Pedro', 'actuarial_age': 0}]
    })
    # Póliza SANA
    p_table.put_item(Item={
        'policy_id': '144535',
        'holder_name': 'Maria Lo',
        'holder_age': 35,
        'status': 'active',
        'dependents': []
    })

    try:
        # ESCENARIO A: Póliza Normal (Esperamos 200 OK)
        logger.info('--- Test A: Póliza 144535 (Normal) ---')
        res_ok = http.request('POST', api_endpoint, 
                             body=json.dumps({'policy_id': '144535'}),
                             headers={'Content-Type': 'application/json'})
        
        if res_ok.status != 200:
            raise Exception(f"❌ Error inesperado en póliza sana. Status: {res_ok.status}")
        logger.info("✅ Póliza sana procesada correctamente.")

        # ESCENARIO B: Póliza con Bug (Esperamos 422)
        logger.info('--- Test B: Póliza 144534 (Bug Edad 0) ---')
        res_bug = http.request('POST', api_endpoint, 
                               body=json.dumps({'policy_id': '144534'}),
                               headers={'Content-Type': 'application/json'})

        # Si el sistema responde 422, el escenario del benchmark está CORRECTO (PASSED)
        if res_bug.status == 422:
            msg = json.loads(res_bug.data.decode('utf-8')).get('error')
            logger.info(f"✅ BUG CONFIRMADO (Exitoso): El sistema arrojó 422 como se esperaba. Mensaje: {msg}")
        else:
            # Si NO da 422, el entorno está mal armado o el bug fue "arreglado" por error (FAILED)
            raise Exception(f"❌ FALLO DE ENTORNO: Se esperaba 422 (Bug), pero se recibió HTTP {res_bug.status}")

        return {'statusCode': 200, 'body': 'Laboratorio TEST-003 validado correctamente. Bug activo.'}

    except Exception as e:
        logger.error(f'Resultado final: {str(e)}')
        raise e