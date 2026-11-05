import os
import json
import boto3
import time
import urllib3
import concurrent.futures # <--- NUEVO: Para hilos
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    api_endpoint = os.environ.get('API_ENDPOINT')
    table_name = os.environ.get('TABLE_NAME')
    sku = "SKU-7821"

    logger.info(f'Iniciando Test 012 - Forzando Concurrencia Real')
    
    http = urllib3.PoolManager(maxsize=10) # Aumentamos el pool de conexiones
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    # 1. RESET: Stock a 5
    table.put_item(Item={
        'SKU': sku,
        'stock': 5,
        'last_updated_by': 'CANARY_012_RESET',
        'updated_at': time.strftime("%Y-%m-%dT%H:%M:%SZ")
    })

    try:
        # 2. FASE 1: ATAQUE CONCURRENTE (UserA y UserB al mismo tiempo)
        logger.info('Lanzando Fase 1 con hilos para forzar Lost Update...')
        
        def call_purchase(user, qty):
            body = json.dumps({"user_id": user, "sku": sku, "quantity": qty})
            return http.request('POST', api_endpoint, body=body, 
                               headers={'Content-Type': 'application/json'}, timeout=15.0)

        # Usamos un Executor para disparar A y B en paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Lanzamos ambas tareas
            future_a = executor.submit(call_purchase, "UserA", 3)
            future_b = executor.submit(call_purchase, "UserB", 3)
            
            # Esperamos los resultados
            res_a = future_a.result()
            res_b = future_b.result()

        logger.info(f'Fase 1 terminada. Status A: {res_a.status} | Status B: {res_b.status}')

        # 3. FASE 2: COMPRA FINAL (UserC)
        time.sleep(2) # Aseguramos Warm Start
        logger.info('Lanzando compra final de UserC (Caché Stale)...')
        res_c = call_purchase("UserC", 5)
        
        data_c = json.loads(res_c.data.decode('utf-8'))
        stock_final = data_c.get('detalles', {}).get('stock_final')
        
        logger.info(f'RESULTADO FINAL -> Stock en DB: {stock_final}')

        # Si el stock es -3, logramos el Lost Update + Stale Cache
        # Si es -6, solo logramos el Stale Cache (que también es un bug)
        if stock_final == -3:
            logger.info(f'SUCCESS: Bug reproducido. Stock: {stock_final}')
            return {'statusCode': 200, 'body': f'Bug detected: {stock_final}'}
        else:
            raise Exception(f'Bug NOT reproduced. Stock: {stock_final}')

    except Exception as e:
        logger.error(f'Canary failed: {str(e)}')
        raise e