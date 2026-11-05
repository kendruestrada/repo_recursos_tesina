## [Titulo]: Timeout en sincronización de permisos por bloqueo en petición HTTP
### Resumen: La función encargada de sincronizar los permisos (Lambda B) sufre un timeout debido a que la petición al procesador externo carece de un tiempo de espera máximo.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir:
  1. Se emite un evento de creación de suscripción (POST) hacia la Lambda A con los datos del usuario.
  2. La Lambda A almacena el registro en DynamoDB con éxito.
  3. El evento de inserción (INSERT) dispara automáticamente la Lambda B mediante DynamoDB Streams.
  4. La Lambda B lee el registro e intenta comunicarse de manera síncrona con un endpoint externo usando la librería `requests`.
  5. La solicitud de red se queda esperando indefinidamente, consumiendo el tiempo máximo de ejecución configurado para la función (10 segundos) hasta que el proceso es finalizado por el servicio, entrando en un bucle de reintentos por parte de DynamoDB.
- Esperado vs. Actual: Se esperaba que, tras la inserción en DynamoDB, la Lambda B confirmara la solicitud al endpoint externo y luego añadiera el usuario al grupo de Cognito correspondiente. Actualmente, la ejecución se interrumpe abruptamente al alcanzar el límite de tiempo (10000 ms), impidiendo que la asignación de permisos a `premium_users` se lleve a cabo.
- Ubicacion del error: Archivo `lambda_b/lambda_function.py`, dentro de la función `lambda_handler`, específicamente en la línea `processor_response = requests.get(processor_url)` donde no se define un límite de tiempo.
- Logs relevantes:
  - `[INFO] Starting Cognito group assignment for user: canary-user-1772045702` (Se inicia el proceso antes de la llamada HTTP).
  - `REPORT RequestId: 1b2d09b9-7a26-429f-b4c3-57eebd923582 Duration: 10000.00 ms Billed Duration: 10000 ms Memory Size: 128 MB Max Memory Used: 86 MB Status: timeout` (La función es interrumpida forzosamente antes de imprimir la respuesta).
### Propuesta de Solucion
1. Modificar la llamada de red en `lambda_b/lambda_function.py` para incluir un parámetro de tiempo de espera explícito. Ejemplo: `requests.get(processor_url, timeout=5)`.
2. Capturar explícitamente las excepciones de red (`requests.exceptions.RequestException`) para manejar fallos del servicio externo de manera controlada y permitir que el mensaje se descarte o se envíe a una cola de mensajes muertos (DLQ) sin bloquear el procesamiento del Stream de DynamoDB.
3. Revisar el estado y disponibilidad del servicio externo apuntado por la variable de entorno `PROCESSOR_ENDPOINT_URL`, ya que su falta de respuesta es el desencadenante principal de la falla del sistema.

# Token Usage

Total Tokens: 72297
Prompt Tokens: 68698
Input Tokens (non-cached): 40337
Response Tokens: 849
Cached Tokens: 28361
Thoughts Tokens: 2750

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.080674
Cached Cost (USD):  $0.005672
Output Cost (USD):  $0.010188
Thoughts Cost (USD):$0.033000
Total Cost (USD):   $0.129534


# Execution time in seconds:

69
