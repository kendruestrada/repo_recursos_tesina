## [Titulo]: Bloqueo en Invalidación de Caché por Petición HTTP sin Timeout
### Resumen: La función encargada de invalidar la caché realiza una llamada de red síncrona a una API externa sin definir un tiempo de espera, lo que bloquea la ejecución e impide que los precios se actualicen en Redis.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir:
  1. Se actualiza el precio de un producto en base de datos mediante la función de actualización de precios.
  2. El cambio genera un evento de DynamoDB Stream que invoca la función de invalidación de caché.
  3. Dentro del ciclo de procesamiento, el código ejecuta una petición HTTP con `requests.get(PROCESSOR_API_URL)` sin establecer un parámetro de "timeout".
  4. Si el servicio de la API externa experimenta lentitud o no responde, la petición se bloquea de forma indefinida.
  5. Este bloqueo agota el tiempo de ejecución de la Lambda, impidiendo que el código alcance la instrucción `redis_client.delete(cache_key)` para borrar el caché.
  6. El usuario visualiza el precio antiguo desde la caché e intenta realizar el pago, siendo rechazado en el flujo de checkout al detectarse una discrepancia con el precio real de la base de datos.
- Esperado vs. Actual:
  - Esperado: La caché debe eliminarse de manera inmediata tras un cambio en la base de datos. Las integraciones con APIs de terceros no deben congelar ni interrumpir el flujo crítico del sistema.
  - Actual: La ejecución se detiene totalmente por la falta de un límite de tiempo en la conexión HTTP externa, provocando que los registros en Redis queden desactualizados y causando el fallo de procesos de compra legítimos.
- Ubicacion del error: `cache_invalidation/app.py` (función `lambda_handler`).
- Logs relevantes:
  - `Inconsistencia de precio detectada` (Generado por `inventory_check/app.py` al comparar un precio de caché obsoleto contra base de datos).
  - `Checkout rechazado por inconsistencia de precio` (Generado por `checkout/app.py`).
  - Ausencia de la traza `Cache invalidado` en la función de invalidación, demostrando que la ejecución no concluye.
### Propuesta de Solucion
- Agregar obligatoriamente el parámetro de límite de tiempo en la librería requests, por ejemplo: `requests.get(PROCESSOR_API_URL, timeout=3)`.
- Reestructurar el código para ejecutar el borrado de la caché `redis_client.delete(cache_key)` inmediatamente después de extraer las variables de evento, y antes de hacer la llamada HTTP externa. Esto asegura la consistencia de los datos en el sistema interno primero.
- Considerar mover el llamado de la API a una arquitectura asíncrona (como enviar un mensaje a una cola SQS o a EventBridge) para no penalizar el tiempo de respuesta ni afectar la capacidad de procesar múltiples eventos en lote del DynamoDB Stream.

# Token Usage

Total Tokens: 22792
Prompt Tokens: 13356
Input Tokens (non-cached): 5275
Response Tokens: 671
Cached Tokens: 8081
Thoughts Tokens: 8765

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.010550
Cached Cost (USD):  $0.001616
Output Cost (USD):  $0.008052
Thoughts Cost (USD):$0.105180
Total Cost (USD):   $0.125398


# Execution time in seconds:

118
