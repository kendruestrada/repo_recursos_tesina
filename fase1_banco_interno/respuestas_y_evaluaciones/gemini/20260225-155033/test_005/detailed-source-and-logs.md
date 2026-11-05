## [Titulo]: Múltiples solicitudes de crédito bloqueadas en estado "pending" debido a falta de actualización de base de datos y timeouts de ejecución
### Resumen: Las solicitudes quedan en "pending" porque RiskAnalysis experimenta un timeout al hacer una llamada HTTP externa sin límite de espera, y porque CreditEvaluation omite la lógica de actualización en DynamoDB posterior a una evaluación.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir:
  1. Enviar una petición inicial para el inicio del flujo con el payload `{"credit_id": "123"}`.
  2. `CreditEvaluation` inserta la solicitud en la tabla DynamoDB con el valor "pending" en la columna status.
  3. `CreditEvaluation` invoca sincrónicamente ("RequestResponse") a la Lambda `RiskAnalysis`.
  4. `RiskAnalysis` obtiene el registro e invoca un servicio externo empleando `requests.get(PROCESSOR_URL)` sin establecer un parámetro de timeout.
  5. Si el servicio externo tiene demoras severas o no responde, la ejecución se bloquea de forma indefinida hasta que AWS interrumpe de forma abrupta a ambas Lambdas tras agotar el límite de ejecución (10 segundos), dejando permanentemente la solicitud como "pending".
  6. Si por el contrario el servicio externo responde en tiempo, la Lambda `CreditEvaluation` carece de cualquier bloque de código posterior que invoque a DynamoDB para cambiar el estado "pending" a un estado de evaluación final tras obtener un 200 OK.
- Esperado vs. Actual:
  - Ejecución hipotética (Entrada): Envío del payload `{"credit_id": "999"}`.
  - Ejecución hipotética (Salida esperada): El servicio externo de evaluación responde un JSON en 2 segundos. `CreditEvaluation` toma dicho resultado positivo y actualiza mediante `update_item` el estado de la solicitud "999" en DynamoDB pasando de "pending" a "processed". Retorna 200.
  - Ejecución hipotética (Salida actual): La llamada a requests de RiskAnalysis se queda atascada sin reaccionar. A los 10 segundos exactos el sistema fuerza un error de timeout. Incluso en escenarios de respuestas rápidas con status code 200, el flujo retorna omitiendo por completo actualizar el valor en la base de datos, lo que hace que todas las solicitudes permanezcan eternamente "en proceso".
- Ubicacion del error (file/function):
  - Fichero `src/risk/app.py` en la función `lambda_handler` (línea `processor_response = requests.get(PROCESSOR_URL)`).
  - Fichero `src/credit/app.py` en la función `lambda_handler` (faltan sentencias para el escenario donde `status_code == 200`).
- Logs relevantes:
  - `Invocando endpoint processor` (Última línea reportada en la lambda de análisis previo al cuelgue).
  - `REPORT RequestId: ... Duration: 10000.00 ms ... Status: timeout` (Evento observable al mismo tiempo en ambos grupos de logs `/aws/lambda/test-005-RiskAnalysis` y `/aws/lambda/test-005-CreditEvaluation`).

### Propuesta de Solucion
1. En el archivo `src/risk/app.py` se debe especificar un tiempo límite al llamar la librería de requests para que aborte la conexión antes del timeout de la lambda. Ejemplo: `requests.get(PROCESSOR_URL, timeout=4)`. Y controlar la excepción que lanza para emitir un status 504 o 503 correctamente manejado.
2. En el archivo `src/credit/app.py` se debe incorporar la lógica pertinente en el paso de flujo feliz para ejecutar un `table.update_item(...)` contra la tabla de DynamoDB, cambiando la columna status de "pending" al estado devuelto tras procesarse el crédito.
3. Se recomienda revisar el diseño de la arquitectura para reemplazar la invocación RequestResponse por llamadas asíncronas con uso de Amazon SQS o EventBridge. Al encadenar funciones Lambda de forma sincrónica se duplican los tiempos cobrados, provocando caídas en cascada donde el tiempo de una se consume íntegramente de la otra.

# Token Usage

Total Tokens: 137820
Prompt Tokens: 131264
Input Tokens (non-cached): 41696
Response Tokens: 1077
Cached Tokens: 89568
Thoughts Tokens: 5479

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.083392
Cached Cost (USD):  $0.017914
Output Cost (USD):  $0.012924
Thoughts Cost (USD):$0.065748
Total Cost (USD):   $0.179978


# Execution time in seconds:

114
