import os
import json
import random
import boto3
import urllib3
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    """
    Manejador Canary Test_006 para replicación del bug de inconsistencia de precios
    siguiendo estrictamente los pasos solicitados.
    """
    api_endpoint = os.environ.get('API_ENDPOINT')
    table_name = os.environ.get('TABLE_NAME')

    if not api_endpoint:
        raise ValueError("La variable de entorno API_ENDPOINT debe estar definida")
    if not table_name:
        raise ValueError("La variable de entorno TABLE_NAME debe estar definida")

    id_suffix = random.randint(1, 1000)
    product_id = f"PROD-{id_suffix:03d}"
    initial_price = random.randint(100, 200)
    # Asegurar que sea diferente y menor (solo para coincidir con el concepto de "rebaja")
    updated_price = random.randint(50, 99) 

    logger.info(f"Iniciando replicación del bug para el producto: {product_id}")
    logger.info(f"Precio inicial: {initial_price}, Precio actualizado: {updated_price}")

    dynamodb = boto3.client('dynamodb')
    http = urllib3.PoolManager()

    # Paso 1: Crear producto con precio inicial
    logger.info("### Paso 1: Crear producto con precio inicial")
    dynamodb.put_item(
        TableName=table_name,
        Item={
            "productId": {"S": product_id},
            "price": {"N": str(initial_price)},
            "stock": {"N": "10"}
        }
    )
    logger.info(f"Producto creado: {product_id} a ${initial_price}")

    # Paso 2: Consultar precio (cache miss -> db)
    logger.info("### Paso 2: Consultar precio (fallo de caché -> bd)")
    url_get = f"{api_endpoint}/product/{product_id}/price"
    resp_get = http.request('GET', url_get)
    if resp_get.status != 200:
        raise Exception(f"Fallo al obtener precio: {resp_get.status} {resp_get.data.decode('utf-8')}")
    
    data_get = json.loads(resp_get.data.decode('utf-8'))
    logger.info(f"Respuesta Paso 2: {data_get}")
    
    if float(data_get['price']) != float(initial_price) or data_get['source'] != 'database':
        raise Exception(f"Fallo en Paso 2: Se esperaba precio {initial_price} desde base de datos, se obtuvo {data_get}")

    # Paso 3: Admin actualiza precio
    logger.info("### Paso 3: Admin actualiza precio (rebaja)")
    url_put = f"{api_endpoint}/admin/product/{product_id}/price"
    resp_put = http.request(
        'PUT', 
        url_put,
        headers={'Content-Type': 'application/json'},
        body=json.dumps({"price": updated_price})
    )
    
    data_put = json.loads(resp_put.data.decode('utf-8'))
    logger.info(f"Respuesta Paso 3: {data_put}")
    
    if not data_put.get('success'):
        raise Exception(f"Fallo en Paso 3: Actualización fallida {data_put}")

    # Paso 4: Consultar precio inmediatamente (BUG EXPECTED)
    logger.info("### Paso 4: Consultar precio inmediatamente (Confirmando Bug)")
    resp_bug = http.request('GET', url_get)
    data_bug = json.loads(resp_bug.data.decode('utf-8'))
    logger.info(f"Respuesta Paso 4: {data_bug}")

    # CONDICIÓN DEL BUG: El precio debe ser el ANTIGUO y la fuente debe ser CACHÉ
    # Para cumplir con "replicar el error", ASEGURAMOS que obtuvimos el precio INCORRECTO desde el caché.
    if float(data_bug['price']) == float(initial_price) and data_bug['source'] == 'cache':
        logger.info("BUG REPLICADO: Precio desactualizado servido desde caché.")
    else:
        # Si obtenemos el precio nuevo o fuente DB, el bug NO se ha replicado
        raise Exception(f"Fallo al replicar el bug: Se obtuvo {data_bug}, se esperaba precio desactualizado {initial_price} desde caché.")

    # Paso 5: Intentar checkout con precio del cache (REJECTION EXPECTED)
    logger.info("### Paso 5: Intentar checkout con precio del cache")
    url_checkout = f"{api_endpoint}/checkout"
    resp_checkout = http.request(
        'POST',
        url_checkout,
        headers={'Content-Type': 'application/json'},
        body=json.dumps({
            "productId": product_id,
            "price": initial_price, # Usando el precio DESACTUALIZADO
            "quantity": 1
        })
    )
    
    data_checkout = json.loads(resp_checkout.data.decode('utf-8'))
    logger.info(f"Respuesta Paso 5: {data_checkout}")

    # ESPERADO: Success=False, Error="Precio manipulado o desactualizado"
    if data_checkout.get('success') is False:
        # Validación estricta del mensaje de error y detalles
        if data_checkout.get('error') != "Precio manipulado o desactualizado":
             raise Exception(f"Fallo en Paso 5: Mensaje de error incorrecto. Se obtuvo: {data_checkout.get('error')}")
        
        details = data_checkout.get('details', {})
        if details.get('error') != "Precio manipulado o desactualizado":
            raise Exception("Fallo en Paso 5: Detalles del error incorrectos")
            
        # Nota: expectedPrice en la respuesta del backend se refiere al precio enviado (el que el backend "esperaba" verificar)
        # y actualPrice al precio real en base de datos.
        if float(details.get('actualPrice')) != float(updated_price):
             raise Exception(f"Fallo en Paso 5: actualPrice {details.get('actualPrice')} no coincide con el precio actualizado {updated_price}")
             
    else:
        raise Exception(f"Fallo al replicar rechazo de checkout. Respuesta: {data_checkout}")

    return {
        "statusCode": 200,
        "body": json.dumps("Replicación del bug exitosa")
    }
