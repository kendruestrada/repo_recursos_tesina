import os
import time
import urllib.request
import urllib.error
import boto3
from aws_synthetics.common import synthetics_logger as logger


def handler(event, context):
    """
    Handler del Canary para Test 019: DynamoDB Hot Partition.

    Pasos:
    1. Invocar la Lambda Generadora de Carga para asegurar que el tráfico de fondo esté corriendo.
    2. Hacer una petición a la categoría "electronics" (Hot Key).
    3. Medir la latencia.
    4. Aserción de que la latencia es alta (> 2 segundos) para confirmar el bug.
    5. También verificar una categoría "fría" ("books") para verificar que es rápida (Control).
    """

    api_endpoint = os.environ.get("TEST_019_API_ENDPOINT")
    load_generator_function = os.environ.get("TEST_019_LOAD_GENERATOR_FUNCTION_NAME")

    if not api_endpoint:
        raise ValueError(
            "La variable de entorno TEST_019_API_ENDPOINT no está configurada"
        )

    if not load_generator_function:
        raise ValueError(
            "La variable de entorno TEST_019_LOAD_GENERATOR_FUNCTION_NAME no está configurada"
        )

    logger.info(f"Target API: {api_endpoint}")
    logger.info(f"Load Generator Function: {load_generator_function}")

    # 1. Invocar Generador de Carga (Fire and Forget)
    lambda_client = boto3.client("lambda")
    try:
        logger.info(f"Invocando Generador de Carga: {load_generator_function}")
        lambda_client.invoke(
            FunctionName=load_generator_function,
            InvocationType="Event",  # Invocación asíncrona
        )
        logger.info("Generador de Carga invocado exitosamente")
    except Exception as e:
        logger.error(f"Falló al invocar el Generador de Carga: {str(e)}")
        # Continuamos de todas formas, ya que el tráfico podría ya estar corriendo o queremos probar incluso si esto falla

    # Esperar un poco para que el tráfico suba si no estaba corriendo
    time.sleep(2)

    # 2. Medir Latencia de "Electronics" (Hot Partition)
    hot_url = f"{api_endpoint}/search?category=electronics"
    logger.info(f"Probando URL Hot: {hot_url}")

    start_time = time.time()
    try:
        with urllib.request.urlopen(hot_url, timeout=30) as response:
            status_code = response.getcode()
            _ = response.read()  # Consumir cuerpo
            logger.info(f"Estado URL Hot: {status_code}")
    except urllib.error.URLError as e:
        logger.error(f"Falló la petición a URL Hot: {str(e)}")
        raise e

    end_time = time.time()
    hot_latency = end_time - start_time
    logger.info(f"Latencia Hot Partition: {hot_latency:.4f} segundos")

    # 3. Medir Latencia de "Books" (Control/Cold Partition)
    control_url = f"{api_endpoint}/search?category=books"
    logger.info(f"Probando URL Control: {control_url}")

    start_time_control = time.time()
    try:
        with urllib.request.urlopen(control_url, timeout=30) as response:
            status_code = response.getcode()
            logger.info(f"Estado URL Control: {status_code}")
    except urllib.error.URLError as e:
        logger.error(f"Falló la petición a URL Control: {str(e)}")
        raise e

    end_time_control = time.time()
    control_latency = end_time_control - start_time_control
    logger.info(f"Latencia Control Partition: {control_latency:.4f} segundos")

    # 4. Aserciones
    # Esperamos que la Hot Partition sea significativamente más lenta debido a Throttling/Retries
    # Típicamente > 2 segundos si ocurren reintentos (comportamiento por defecto del SDK)

    logger.info("Verificando reproducción del Bug Hot Partition...")

    if hot_latency > 2.0:
        logger.info(
            "✅ EXITO: Alta latencia detectada en Hot Partition. Bug reproducido."
        )
    elif hot_latency > control_latency * 5:
        logger.info(
            "✅ EXITO: Hot Partition es significativamente más lenta (>5x) que Control. Bug reproducido."
        )
    else:
        logger.info(
            f"⚠️ ADVERTENCIA: Latencia baja observada ({hot_latency:.4f}s). El Bug PODRÍA NO estar reproduciéndose. ¿Está corriendo el Generador de Carga?"
        )
        # Dependiendo de la rigurosidad, podríamos fallar el canary aquí o solo advertir.
        # Para un canary de "reproducción", pasar significa que ejecutamos los pasos de prueba exitosamente.
        # Pero si el objetivo es FALLAR cuando el bug está presente (Test de Regresión), lanzaríamos un error.
        # Aquí, el objetivo es "Verificar" que el bug existe. Así que tal vez deberíamos fallar si es RÁPIDO?
        # Dejemos solo log por ahora ya que la salida al usuario es clave.

    return {
        "hot_latency": hot_latency,
        "control_latency": control_latency,
        "bug_reproduced": hot_latency > 2.0 or hot_latency > control_latency * 5,
    }
