## Timeout en DynamoDB Stream bloquea invalidación de caché
### Resumen: La función Lambda encargada de invalidar la caché no logra procesar todos los registros de un lote debido a llamadas HTTP síncronas muy lentas y sin límite de tiempo, causando un bloqueo infinito en el stream y dejando precios desactualizados en Redis.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir:
1. Se actualizan los precios de uno o más productos a través de la API de actualización.
2. DynamoDB Stream agrupa las modificaciones en un lote (batch) y lo envía a la función `CacheInvalidationFunction`.
3. La función itera sobre cada registro del lote de manera secuencial.
4. Para cada iteración, se realiza una petición bloqueante mediante `requests.get(PROCESSOR_API_URL)` sin parámetro de timeout. Esta petición tarda aproximadamente 15 segundos en completarse.
5. Al intentar procesar un segundo registro dentro del mismo lote, el tiempo total de ejecución supera el límite configurado de la función Lambda (20 segundos), provocando que esta termine forzosamente por un Timeout.
6. Como la función falla, DynamoDB reintenta el mismo lote indefinidamente (comportamiento conocido como "Poison Pill"), bloqueando el flujo. 
7. En consecuencia, la clave en Redis no se elimina y el componente `ProductPricingFunction` continúa retornando el precio antiguo a los clientes, desencadenando posteriormente un error de "Precio manipulado o desactualizado" en el flujo de `CheckoutFunction`.

- Esperado vs. Actual:
Esperado: Que la función de invalidación procese todos los eventos del lote en el tiempo provisto (20s), elimine la caché correctamente para cada producto, y que DynamoDB avance hacia los siguientes registros del stream.
Actual: La petición HTTP agota el tiempo de ejecución, el lote completo se marca como fallido, y entra en un ciclo de reintentos infinitos. Las cachés nunca llegan a invalidarse, generando inconsistencias de precios durante el checkout.

- Ubicacion del error (file/function):
File: `@cache_invalidation/app.py`
Function: `lambda_handler` (línea donde se encuentra `requests.get(PROCESSOR_API_URL)`)

- Logs relevantes:
```json
{"level":"INFO", "message":"Cambio de precio detectado en DynamoDB Stream", "productId":"PROD-985", "timestamp":"2026-02-25 16:11:15,296+0000"}
{"level":"INFO", "message":"Llamada a API externa completada", "statusCode":200, "timestamp":"2026-02-25 16:11:30,417+0000"}
{"level":"INFO", "message":"Cambio de precio detectado en DynamoDB Stream", "productId":"PROD-406", "timestamp":"2026-02-25 16:11:30,424+0000"}
REPORT RequestId: bf9a4782-2d52-4e92-89e3-e1a4705ec7e7 Duration: 20000.00 ms Billed Duration: 20000 ms Memory Size: 256 MB Max Memory Used: 79 MB Status: timeout
```
*(Los logs de dev-InventoryCheckFunction evidencian luego el síntoma secundario: "Inconsistencia de precio detectada")*

### Propuesta de Solucion
1. Agregar el parámetro `timeout` a la petición HTTP para evitar que bloquee la ejecución. Por ejemplo: `requests.get(PROCESSOR_API_URL, timeout=2)`.
2. Reordenar el flujo de ejecución para eliminar la caché en Redis (`redis_client.delete(cache_key)`) antes de intentar consumir la API externa, asegurando así que el sistema principal siempre quede consistente en caso de fallo externo.
3. Desacoplar la llamada a la API externa utilizando AWS SQS o EventBridge, permitiendo que la invalidación de caché en Redis ocurra de inmediato de forma independiente.
4. Configurar manejo de fallos en el DynamoDB Stream dentro de `template.yaml` limitando los reintentos mediante `MaximumRetryAttempts` o enviando los registros fallidos a una cola DLQ (Dead Letter Queue) a través de `DestinationConfig`, evitando el bloqueo por "poison pill".

# Token Usage

Total Tokens: 403718
Prompt Tokens: 397898
Input Tokens (non-cached): 120009
Response Tokens: 1294
Cached Tokens: 277889
Thoughts Tokens: 4526

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.240018
Cached Cost (USD):  $0.055578
Output Cost (USD):  $0.015528
Thoughts Cost (USD):$0.054312
Total Cost (USD):   $0.365436


# Execution time in seconds:

117
