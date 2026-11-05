import os
import json
import boto3
import time
import urllib3
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    api_endpoint = os.environ.get('API_ENDPOINT')
    user_pool_id = os.environ.get('USER_POOL_ID')
    table_name = os.environ.get('TABLE_NAME')
    group_name = "premium_users" # Coincide con tu Lambda B
    
    unique_user_id = f"canary-user-{int(time.time())}"
    user_email = f"{unique_user_id}@example.com"
    
    http = urllib3.PoolManager()
    dynamo = boto3.client('dynamodb')
    cognito = boto3.client('cognito-idp')

    # Variable para rastrear si el usuario fue creado y debe ser limpiado
    user_created = False

    try:
        # PASO 0: Crear el usuario en Cognito con los atributos obligatorios
        logger.info(f'Paso 0: Creando usuario {unique_user_id} en Cognito...')
        cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=unique_user_id,
            UserAttributes=[
                {'Name': 'email', 'Value': user_email},
                {'Name': 'email_verified', 'Value': 'true'}
            ],
            MessageAction='SUPPRESS'
        )
        user_created = True

        # PASO 1: Llamar a tu Lambda A vía API
        logger.info(f'Paso 1: Llamando a API de suscripción para {unique_user_id}...')
        payload = {"user_id": unique_user_id, "plan_type": "premium"}
        response = http.request(
            'POST', api_endpoint, 
            body=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=10.0
        )

        if response.status != 200:
            raise Exception(f"La API respondió con error {response.status}")

        # PASO 2: Esperar el fallo de tu Lambda B (que tarda 4s pero muere a los 3s)
        logger.info('Paso 2: Esperando 15s para que ocurra el timeout asíncrono y los retries...')
        time.sleep(15)

        # PASO 3: Validar estado en DynamoDB
        logger.info('Paso 3: Verificando estado en DynamoDB...')
        db_res = dynamo.get_item(TableName=table_name, Key={'user_id': {'S': unique_user_id}})
        db_item = db_res.get('Item', {})
        db_status = db_item.get('subscription_status', {}).get('S', 'NOT_FOUND')
        
        # PASO 4: Validar grupos en Cognito
        logger.info('Paso 4: Verificando grupos en Cognito...')
        cog_res = cognito.admin_list_groups_for_user(Username=unique_user_id, UserPoolId=user_pool_id)
        groups = [g['GroupName'] for g in cog_res.get('Groups', [])]

        logger.info(f"VALIDACIÓN FINAL -> DynamoDB: {db_status} | Grupos Cognito: {groups}")

        # PASO 5: Confirmar Inconsistencia
        # El bug es exitoso si DB es active pero Cognito NO tiene el grupo
        bug_reproducido = (db_status == "active" and group_name not in groups)

        if bug_reproducido:
            logger.info("✅ TEST EXITOSO: Inconsistencia detectada (DB activa, Cognito vacío).")
            return {"body": "Bug verified"}
        else:
            if group_name in groups:
                raise Exception(f"❌ ERROR: El usuario YA tiene el grupo '{group_name}'. La sincronización funcionó (bug no reproducido).")
            else:
                raise Exception(f"❌ ERROR: Estado inconsistente no detectado. DB Status: {db_status}")

    except Exception as e:
        logger.error(f"Error en Canary: {str(e)}")
        raise e

    finally:
        # PASO 6: LIMPIEZA (Siempre se ejecuta para mantener el User Pool limpio)
        if user_created:
            try:
                logger.info(f'Iniciando limpieza del usuario {unique_user_id}...')
                cognito.admin_delete_user(UserPoolId=user_pool_id, Username=unique_user_id)
                
                # Intentar borrar de DynamoDB si Lambda A alcanzó a escribir
                dynamo.delete_item(TableName=table_name, Key={'user_id': {'S': unique_user_id}})
                logger.info('Limpieza completada con éxito.')
            except Exception as clean_ex:
                logger.warn(f'Advertencia durante la limpieza: {str(clean_ex)}')