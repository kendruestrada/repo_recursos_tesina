import os
import json
import urllib3
import time
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    logger.info("Iniciando Reproducción: Test 013 (Connection Leak)")
    
    # Usamos la URL directamente del .env para evitar duplicar el path /process 
    api_url = os.environ.get('API_ENDPOINT')
    http = urllib3.PoolManager(timeout=urllib3.Timeout(connect=5.0, read=35.0))
    
    max_pool_size = 5
    iterations = max_pool_size + 1
    bug_reproduced = False
    durations = [] # Para calcular el promedio de latencia "sana"

    logger.info(f"Target: {api_url} | Iteraciones: {iterations}")

    for i in range(iterations):
        request_idx = i + 1
        try:
            logger.info(f"Petición {request_idx}/{iterations} en curso...")
            start_time = time.time()
            
            response = http.request(
                'POST', 
                api_url,
                body=json.dumps({"test_id": "t13", "cycle": request_idx}),
                headers={'Content-Type': 'application/json'}
            )
            
            duration = time.time() - start_time
            logger.info(f"Intento {request_idx} terminó en {duration:.2f}s (Status: {response.status})")

            # 1. Detección por Contrato: Si el Gateway nos da un 504, es un colapso de infra 
            if response.status == 504:
                logger.info(f"BUG - Timeout de infraestructura detectado en iteración {request_idx}")
                bug_reproduced = True
                break
                
            # 2. Detección por Anomalía: Si es 10 veces más lento que el promedio de las anteriores
            if durations:
                avg_latency = sum(durations) / len(durations)
                if duration > (avg_latency * 10):
                    logger.info(f"ANOMALÍA - Degradación crítica de latencia en iteración {request_idx}")
                    bug_reproduced = True
                    break
            
            # Solo guardamos el tiempo si fue una respuesta exitosa (el sistema estaba "sano")
            if response.status == 200:
                durations.append(duration)

        except Exception as e:
            duration = time.time() - start_time
            logger.info(f"La petición {request_idx} falló tras {duration:.2f}s")
            
            # Respaldo en caso de que el timeout ocurra a nivel de librería de red
            if duration >= 28.0:
                logger.info(f"BUG - El servicio dejó de responder en iteración {request_idx}")
                bug_reproduced = True
                break
            else:
                logger.error(f"Error no relacionado al bug: {str(e)}")
                raise e

    if bug_reproduced:
        logger.info("Escenario de error reproducido exitosamente.")
        return {"status": "success", "detail": f"Resource exhaustion confirmed at iteration {request_idx}"}
    else:
        logger.error("No se pudo reproducir el bug. El sistema liberó las conexiones correctamente.")
        raise Exception("Fallo de reproducción: Todas las peticiones fueron consistentes y rápidas.")