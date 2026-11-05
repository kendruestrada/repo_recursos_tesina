## [Titulo]: Falta de limite de tiempo en peticion HTTP causa timeouts de infraestructura y deja solicitudes huerfanas

### Resumen: La ausencia de un parametro timeout al invocar el servicio externo en la funcion de riesgos agota el tiempo de ejecucion en AWS Lambda, interrumpiendo abruptamente el flujo antes de que la funcion principal pueda actualizar el estado en la base de datos.

### Severidad: High

### Analisis de causa raiz
- **Analisis de expertos e inconsistencias de flujo**: En analisis conjunto con los logs de CloudWatch, evidenciamos que la funcion `RiskAnalysis` ejecuta un requerimiento de red sincrono con `requests.get()` hacia `PROCESSOR_URL` sin establecer un limite de tiempo. Cuando el servicio externo demora mas del timeout configurado (10 segundos), el servicio de infraestructura de AWS Lambda finaliza agresivamente ambos procesos: el propio `RiskAnalysis` y su invocador `CreditEvaluation`. Al romperse la ejecucion esperada, la funcion invocadora nunca alcanza el bloque de logica que actualizaria el estado final ni detecta la anomalia de manera apropiada.
- **Ejemplo de ejecucion**: 
  - *Entrada*: Se envia un evento POST a la API de evaluacion con `{"credit_id": "TEST-123"}`.
  - *Estado intermedio*: `CreditEvaluation` hace `update_item` en DynamoDB con `status="pending"`.
  - *Flujo y excepcion*: `RiskAnalysis` recibe la peticion y llama a `requests.get`. El procesador externo demora 15 segundos en contestar. Al segundo 10, se detiene todo el entorno de ejecucion.
  - *Salida*: El usuario recibe 504 o Gateway Timeout de la API y el registro DynamoDB "TEST-123" queda `pending` por siempre (estado no validado).
- **Pasos para reproducir**:
  1. Emitir una solicitud para creacion de credito a traves del API.
  2. Configurar o simular que el `PROCESSOR_URL` responda de manera excesivamente lenta (mas de 10 segundos).
  3. Revisar CloudWatch Logs para observar el Status: timeout de ambos servicios.
  4. Revisar DynamoDB y constatar que el estatus queda como "pending" y la ejecucion muere silenciosamente en el consumidor inicial.
- **Esperado vs. Actual**:
  Se espera que si un microservicio o dependencia demora en responder, el sistema interrumpa la operacion controladamente (mediante manejo de timeout) y la base de datos se actualice indicando un estado de "error" o "rechazado". Actualmente, un cuello de botella de latencia agota el periodo de la funcion, terminando ambas lambdas sin la posibilidad de manejar el error, dejando la solicitud estancada.
- **Ubicacion del error (file/function)**:
  - `src/risk/app.py`: funcion `lambda_handler`. Modulo donde se llama a `requests.get(PROCESSOR_URL)` omitiendo el parametro timeout.
  - `src/credit/app.py`: funcion `lambda_handler`. Modulo que carece de bloque o compensacion local para actualizar el estado final (ej: `failed` o `error`) si la respuesta no es 200 o si el `invoke` arroja una falla de conectividad/timeout.
- **Logs relevantes**:
  ```text
  /aws/lambda/test-005-RiskAnalysis:
  Invocando endpoint processor
  REPORT RequestId: ... Duration: 10000.00 ms   Billed Duration: 10000 ms ... Status: timeout

  /aws/lambda/test-005-CreditEvaluation:
  REPORT RequestId: ... Duration: 10000.00 ms   Billed Duration: 10000 ms ... Status: timeout
  ```

### Propuesta de Solucion
1. **Configurar limite en peticion HTTP**: Agregar el argumento `timeout` a la funcion `requests.get` en `src/risk/app.py` (ejemplo: `requests.get(PROCESSOR_URL, timeout=4)`), para arrojar una excepcion controlada antes de que muera la funcion Lambda.
2. **Manejar estado de fallo en origen**: Modificar `src/credit/app.py` para que, en caso de recibir un error al invocar a `RiskAnalysis` (incluyendo su bloque de excepcion) o un status code distinto a 200, ejecute una actualizacion sobre la tabla DynamoDB cambiando el campo status de `pending` a `failed` o `error`.
3. **Optimizar Tiempos Limites**: Si es posible, modificar `template.yaml` para asegurar que la funcion `CreditEvaluation` (orquestadora) posea un tiempo de vida nominal ligeramente superior que la funcion de `RiskAnalysis` (por ejemplo, 12 segundos contra 10 segundos). Esto asegura que la lambla invocadora tenga la posibilidad de manejar caidas de sub-rutinas mediante un bloque `except` y guardar estados finales.

# Token Usage

Total Tokens: 111650
Prompt Tokens: 105310
Input Tokens (non-cached): 44226
Response Tokens: 1291
Cached Tokens: 61084
Thoughts Tokens: 5049

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.088452
Cached Cost (USD):  $0.012217
Output Cost (USD):  $0.015492
Thoughts Cost (USD):$0.060588
Total Cost (USD):   $0.176749


# Execution time in seconds:

93
