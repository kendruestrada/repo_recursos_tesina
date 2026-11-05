import os
import json
import boto3
import time
import urllib3
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    api_endpoint = os.environ.get('API_ENDPOINT')
    ssm_parameter_name = os.environ.get('SSM_PARAMETER_NAME')
    
    ssm_client = boto3.client('ssm')
    http = urllib3.PoolManager(retries=False) 

    param = ssm_client.get_parameter(Name=ssm_parameter_name, WithDecryption=True)
    auth_token = param['Parameter']['Value']
    headers = {'X-API-Key': auth_token, 'Content-Type': 'application/json'}
    payload = json.dumps({"orderId": "ORDER-123", "email": "test@mail.com"})

    # FASE 1: Inducción Quirúrgica
    # El objetivo es llegar a 5 fallos y DETENERSE inmediatamente.
    logger.info("Fase 1: Induciendo apertura del circuito...")
    
    circuit_opened = False
    consecutive_errors = 0
    
    for i in range(30):
        try:
            res = http.request('POST', api_endpoint, body=payload, headers=headers, timeout=10.0)
            
            try:
                raw_data = json.loads(res.data.decode('utf-8'))
                inner_data = raw_data
                if 'body' in raw_data and isinstance(raw_data['body'], str):
                    try: inner_data = json.loads(raw_data['body'])
                    except: pass
                
                count = inner_data.get('failureCount', 0)
                state = inner_data.get('circuitBreakerState', 'UNKNOWN')
            except:
                count = 0
                state = "UNKNOWN"

            logger.info(f"Intento {i+1}: Status {res.status} | Contador: {count} | Estado: {state}")

            if res.status >= 500:
                consecutive_errors += 1
            else:
                consecutive_errors = 0 

            # Si el backend confirma OPEN o alcanzamos el umbral (5) por racha
            if state == "OPEN" or consecutive_errors >= 5:
                logger.info("✅ CIRCUITO ABIERTO detectado. Cesando fuego para evitar reset accidental.")
                circuit_opened = True
                break
                
        except Exception as e:
            consecutive_errors += 1
            logger.warning(f"Error de red en intento {i+1}: {str(e)}")
            if consecutive_errors >= 5:
                circuit_opened = True
                break
        
        time.sleep(0.5)

    if not circuit_opened:
        raise Exception("FALLO: El sistema no entró en estado de error. SES está demasiado estable.")

    # FASE 2: Incubación del Estado Zombie
    logger.info("Fase 2: Esperando 7 segundos para que expire la ventana de 'falsa recuperación'...")
    time.sleep(7)

    # FASE 3: Validación Doble de Persistencia y All-or-Nothing
    # Validamos usando un payload que NO necesita email. Debería funcionar, pero el bug lo bloquea.
    payload_safe = json.dumps({"orderId": "ORDER-999", "email": "test@mail.com", "notificationType": "NONE"})

    for v in range(1, 3):
        logger.info(f"Fase 3: Validación {v}/2 (Probando All-or-Nothing)...")
        try:
            val_res = http.request('POST', api_endpoint, body=payload_safe, headers=headers, timeout=10.0)
            val_body = val_res.data.decode('utf-8')
            
            if val_res.status == 503 and "Circuit breaker is OPEN" in val_body:
                logger.info(f"Validación {v}: Sistema bloqueado incluso para peticiones sin email. (Estado Zombie y All-or-Nothing confirmados).")
            else:
                raise Exception(f"FALLO: El sistema no se bloqueó correctamente en validación {v}. Status: {val_res.status}")
            
        except Exception as e:
            if "Circuit breaker is OPEN" in str(e):
                logger.info(f"Validación {v}: Bloqueo confirmado vía mensaje de excepción.")
            else:
                raise e

        if v == 1:
            logger.info("Esperando 10 segundos adicionales para re-confirmar el bloqueo permanente...")
            time.sleep(10)

    logger.info("BUG REPRODUCIDO: El sistema ha quedado bloqueado permanentemente.")
    return {"body": "Test 007: state verified"}