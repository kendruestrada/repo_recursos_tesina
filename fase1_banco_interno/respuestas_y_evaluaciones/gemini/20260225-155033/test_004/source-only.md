## [Titulo]: Falla en manejo de eventos fallidos hacia DLQ y error de tipo en peticiones vacías
### Resumen: La arquitectura descarta registros fallidos de DynamoDB en lugar de enviarlos a la DLQ, y la API de suscripción falla con código HTTP 500 al recibir peticiones sin cuerpo.
### Severidad: High
### Analisis de causa raiz
El equipo de expertos analizó la arquitectura y el código detectando las siguientes inconsistencias:
- Flujo de eventos síncronos: La función Lambda B es invocada de forma síncrona por DynamoDB Streams. Configurar `DeadLetterQueue` a nivel de función en la plantilla SAM solo captura errores de invocaciones asíncronas. Por tanto, cuando Lambda B lanza una excepción intencional para ir a la DLQ, el evento simplemente se reintenta según `MaximumRetryAttempts` y luego se descarta permanentemente.
- Tipos de datos en API: Cuando API Gateway recibe una petición vacía, el campo `body` en el evento es `null` (None en Python). Usar `event.get("body", "{}")` en Lambda A retorna `None`, causando que `json.loads(None)` lance un `TypeError` y rompa el flujo esperado.
- Conexiones bloqueantes: La llamada externa a `requests.get` en Lambda B carece de un límite de tiempo (timeout), lo que puede congelar la ejecución de la función si el endpoint remoto se queda colgado, agotando los recursos del stream.

- Pasos para reproducir
  1. Para el error de API: Enviar una petición POST a la ruta `/subscription` sin enviar carga útil (body).
  2. Para el error de DLQ: Insertar un registro válido en DynamoDB, pero forzar un error en Lambda B (por ejemplo, asegurar que el usuario no exista en Cognito). Esperar a que el procesamiento agote sus dos reintentos configurados y verificar la SQS.

- Esperado vs. Actual
  - Esperado: Una petición sin cuerpo debe retornar un código HTTP 400 controlado. Los eventos fallidos de la base de datos deben almacenarse en la cola SQS configurada para su inspección.
  - Actual: Una petición sin cuerpo genera una excepción no controlada y retorna un código HTTP 500. Los eventos fallidos de la base de datos se pierden definitivamente tras agotar reintentos sin registrar nada en la SQS.

- Ubicacion del error (file/function)
  - `template.yaml` (Recurso: SyncPermissionsFunction)
  - `lambda_a/lambda_function.py` (Función: lambda_handler, bloque de parseo)
  - `lambda_b/lambda_function.py` (Función: lambda_handler, bloque de petición HTTP)

- Logs relevantes
  - Lambda A: Error generado por el intérprete de Python reportando un fallo TypeError debido a que "the JSON object must be str, bytes or bytearray, not NoneType".
  - Lambda B: Logs mostrando "[ERROR] Failed to sync permissions: ..." seguido del agotamiento silencioso de reintentos por parte del servicio de AWS, sin evidencia de entrega en la DLQ.

### Propuesta de Solucion
- En `template.yaml`, remover la propiedad `DeadLetterQueue` de la configuración raíz de la función Lambda B y configurar su destino en `DestinationConfig > OnFailure` dentro de las propiedades del disparador de DynamoDB.
- En `lambda_a/lambda_function.py`, corregir la asignación de la variable asegurando la evaluación booleana: `body = json.loads(event.get("body") or "{}")`.
- En `lambda_b/lambda_function.py`, incluir un margen de tiempo en la solicitud HTTP para evitar bloqueos: `requests.get(processor_url, timeout=5)`.
- En `lambda_b/lambda_function.py`, remover el formato de retorno estilo API Gateway (con statusCode y body), ya que las funciones disparadas por Streams síncronos no procesan esa respuesta.

# Token Usage

Total Tokens: 36925
Prompt Tokens: 24722
Input Tokens (non-cached): 8584
Response Tokens: 965
Cached Tokens: 16138
Thoughts Tokens: 11238

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.017168
Cached Cost (USD):  $0.003228
Output Cost (USD):  $0.011580
Thoughts Cost (USD):$0.134856
Total Cost (USD):   $0.166832


# Execution time in seconds:

144
