import os
import json
import boto3
import time
import urllib3
import threading
from aws_synthetics.common import synthetics_logger as logger

http = urllib3.PoolManager()
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')

def clean_locks_table(table_name):
    """Limpia la tabla de tracker de forma externa para no dejar rastro en el código fuente."""
    table = dynamodb.Table(table_name)
    scan = table.scan()
    with table.batch_writer() as batch:
        for item in scan.get('Items', []):
            batch.delete_item(Key={'resource_key': item['resource_key']})
    logger.info(f"Escenario limpiado: {len(scan.get('Items', []))} locks eliminados.")

def make_request(url, payload):
    try:
        # Petición diseñada para colisionar
        http.request(
            'POST', url, 
            body=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=75.0 
        )
    except:
        pass

def handler(event, context):
    transfer_url = os.environ.get('TRANSFER_API')
    init_func = os.environ.get('INITIALIZE_FUNCTION')
    locks_table = os.environ.get('LOCKS_TABLE')

    logger.info("Preparando ejecución del Test 016...")

    lambda_client.invoke(FunctionName=init_func, InvocationType='RequestResponse')

    clean_locks_table(locks_table)

    # 3. Ejecutar transacciones cruzadas simultáneas
    t1 = threading.Thread(target=make_request, args=(transfer_url, {"from_account": "A", "to_account": "B"}))
    t2 = threading.Thread(target=make_request, args=(transfer_url, {"from_account": "B", "to_account": "A"}))

    logger.info("Lanzando ataque de Deadlock (A->B y B->A)...")
    t1.start()
    t2.start()

    # 4. Esperar el colapso (Lambda timeout = 60s)
    logger.info("Esperando 75 segundos para confirmar el bloqueo...")
    time.sleep(75)

    # 5. Verificar si el bug se reprodujo
    table = dynamodb.Table(locks_table)
    items = table.scan().get('Items', [])
    
    # Lógica VERDE: Si hay 2 locks, logramos recrear el Deadlock perfectamente.
    if len(items) >= 2:
        logger.info(f"BUG - Se encontraron {len(items)} locks bloqueados.")
        return {'statusCode': 200, 'body': 'Deadlock confirmed'}
    else:
        # Si el sistema está vacío, algo falló en la colisión y el test no es válido.
        msg = "Fallo de reproducción: El sistema no quedó bloqueado."
        logger.error(msg)
        raise Exception(msg)