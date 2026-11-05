import os
import json
import boto3
import urllib3
import time
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    """
    Test_010 Canary Handler
    Limpia la BD, crea un usuario vía API, verifica persistencia 
    y da tiempo para la ejecución asíncrona del Email.
    """
    base_url = os.environ.get('BASE_URL')
    users_table_name = os.environ.get('USERS_TABLE_NAME')
    
    if not base_url or not users_table_name:
        raise ValueError('BASE_URL and USERS_TABLE_NAME environment variables are required')

    logger.info(f'Starting test 010 against: {base_url}')

    test_email = 'preslee.jeancarlo@dropmeon.com'
    
    # ----------------------------------------------------------------
    # 0. FASE DE LIMPIEZA PREVIA (Asegura que el Stream se dispare)
    # ----------------------------------------------------------------
    try:
        logger.info(f'Cleaning up existing record for {test_email}...')
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(users_table_name)
        table.delete_item(
            Key={'email': test_email}
        )
        logger.info('Cleanup successful (or item did not exist).')
    except Exception as e:
        logger.warn(f'Could not delete existing record: {str(e)}')
    # ----------------------------------------------------------------

    payload = {
        'first_name': 'José', 
        'last_name': 'García',
        'birth_date': '1990-01-01',
        'genre': 'M',
        'email': test_email
    }
    
    http = urllib3.PoolManager()
    
    try:
        # 1. Petición POST -> Genera logs en UserRegistrationFunction
        target_url = f"{base_url.rstrip('/')}/users"
        logger.info(f'Making POST request to: {target_url}')
        encoded_data = json.dumps(payload).encode('utf-8')
        
        response_post = http.request(
            'POST',
            target_url,
            body=encoded_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'AWS-Synthetics-Canary-Test010'
            },
            timeout=30.0
        )
        
        if response_post.status not in [200, 201]:
            raise Exception(f'API POST failed with status {response_post.status}')
            
        logger.info('User creation request successful')
        
        # 2. Petición GET -> Genera logs en SearchUsersFunction
        search_url = f"{base_url.rstrip('/')}/users/search?email={test_email}"
        logger.info(f'Making GET request to: {search_url}')
        
        response_get = http.request(
            'GET',
            search_url,
            headers={'User-Agent': 'AWS-Synthetics-Canary-Test010'},
            timeout=30.0
        )
        
        if response_get.status != 200:
            raise Exception(f'API GET failed with status {response_get.status}')
            
        user_record = json.loads(response_get.data.decode('utf-8'))
        logger.info(f'Found user record via API: {user_record}')
        
        if user_record.get('first_name') != 'José':
             logger.warn(f"Mismatch in DB! Expected 'José', got '{user_record.get('first_name')}'")
        
        # 3. Esperar al Stream -> Permite que se generen logs en SendEmailServiceFunction
        logger.info('Waiting 5 seconds for DynamoDB Stream to trigger Email Lambda...')
        time.sleep(5)
        
        return {
            'statusCode': 200,
            'body': 'Test 010 passed: Flow completed and logs generated.'
        }

    except Exception as e:
        logger.error(f'Test failed: {str(e)}')
        raise e