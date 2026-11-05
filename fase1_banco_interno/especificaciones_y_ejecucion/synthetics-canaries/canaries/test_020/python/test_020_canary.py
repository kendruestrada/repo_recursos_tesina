import os
import boto3
import urllib3
import json
import time
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    # Obtenemos la base URL (.../prod/user) y le sumamos /profile
    base_url = os.environ.get('API_URL')
    api_endpoint = f"{base_url.rstrip('/')}/profile"
    ssm_parameter_name = os.environ.get('SSM_PARAMETER_NAME')
    
    logger.info(f'Iniciando Canary en el endpoint: {api_endpoint}')
    
    # Recuperamos el Token desde SSM
    ssm_client = boto3.client('ssm')
    response = ssm_client.get_parameter(Name=ssm_parameter_name, WithDecryption=True)
    token = response['Parameter']['Value']

    http = urllib3.PoolManager()

    try:
        # --- PASO 1: ACTIVAR SESIÓN (Simula Usuario Legítimo) ---
        logger.info('Paso 1: Sincronizando sesion del usuario (Login)')
        
        activate_headers = {
            'Authorization': f'Bearer {token}', # IMPORTANTE: Formato Bearer para JWT
            'ACTIVATE': 'true',
            'Origin': 'https://test-020-frontendbucket.s3.amazonaws.com',
            'User-Agent': 'AWS-Synthetics-Canary'
        }
        
        resp_act = http.request('GET', api_endpoint, headers=activate_headers)
        
        if resp_act.status != 200:
            # Si aquí da 403, el token en el .env es inválido o expiró
            raise Exception(f"Fallo activacion: {resp_act.status}")
        
        logger.info('Sesion activa en Cloud. Esperando persistencia...')
        time.sleep(2) 

        # --- PASO 2: EL ATAQUE (Simula Sitio Malicioso Sigiloso) ---
        logger.info('Paso 2: Iniciando solicitud de datos desde origen externo (Ataque CORS)')
        
        attack_headers = {
            'Authorization': f'Bearer {token}',
            'Origin': 'https://app-rewards-service.io', # Dominio no autorizado
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        resp_attack = http.request('GET', api_endpoint, headers=attack_headers)

        # Si el servidor responde 200 a un Origin malicioso, la vulnerabilidad existe
        if resp_attack.status == 200:
            cors_header = resp_attack.headers.get('Access-Control-Allow-Origin')
            logger.info(f'VULNERABILIDAD DETECTADA: El servidor permitio el origen {cors_header}')
            
            return {
                'statusCode': 200, 
                'body': f'Ataque exitoso. Datos exfiltrados desde {attack_headers["Origin"]}',
                'detected_origin': cors_header
            }
        else:
            logger.info(f'Ataque bloqueado correctamente por el servidor (Status: {resp_attack.status})')
            return {
                'statusCode': resp_attack.status,
                'body': 'CORS funcionando correctamente (Ataque bloqueado)'
            }

    except Exception as e:
        logger.error(f'Error en Canary Test 020: {str(e)}')
        raise e