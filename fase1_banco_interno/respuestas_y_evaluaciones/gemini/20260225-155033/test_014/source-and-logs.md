## Asignación Duplicada de Puntos de Fidelidad
### Resumen: La aplicación registra incorrectamente los puntos debido a invocaciones duplicadas o reintentos que se procesan varias veces, originado por la falta de atomicidad e idempotencia en el código y reglas redundantes en la infraestructura.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir: Emitir un evento de compra a EventBridge o enviar peticiones idénticas casi simultáneas al endpoint `/points` de la API.
- Esperado vs. Actual: Se espera que un usuario reciba los puntos de fidelidad correspondientes a su compra exactamente una vez. Actualmente, las peticiones simultáneas o invocaciones duplicadas suman los puntos múltiples veces.
Ejemplo de ejecución:
  1. Entran Petición A y Petición B (duplicada de la misma compra, con `points_earned: 50`).
  2. El balance inicial es 100.
  3. Petición A procesa, lee 100 y escribe 150.
  4. Petición B procesa inmediatamente después, lee 150 y escribe 200.
  - **Salida esperada:** 150 puntos (se debe descartar la petición duplicada).
  - **Salida actual:** 200 puntos.
- Ubicacion del error (file/function): `src/update_points.py` (función `handler`) y `template.yaml`.
- Logs relevantes:
```text
2026-02-25 18:55:27.133 - Received event: {"resource": "/points", "httpMethod": "POST", ... "body": "{\"detail\": {\"user_id\": \"user_test_14\", \"amount\": 500, \"points_earned\": 50}}"}
2026-02-25 18:55:27.404 - Updated points for user_test_14: 150
2026-02-25 18:55:27.463 - Received event: {"resource": "/points", "httpMethod": "POST", ... "body": "{\"detail\": {\"user_id\": \"user_test_14\", \"amount\": 500, \"points_earned\": 50}}"}
2026-02-25 18:55:27.544 - Updated points for user_test_14: 200
```
Se identifican tres fallas subyacentes:
1. **Condición de Carrera y Parche Inadecuado:** El código lee el estado y luego lo escribe (`get_item` seguido de `put_item`). Para evitar sobreescrituras (Lost Update), se limitó la concurrencia en la lambda a 1 (`ReservedConcurrentExecutions: 1`). Esto fuerza un encolamiento secuencial de todas las peticiones, permitiendo que las invocaciones duplicadas se acumulen.
2. **Falta de Idempotencia:** La aplicación carece de control para detectar eventos ya procesados (ej. falta un transaction ID).
3. **Reglas EventBridge Duplicadas:** En `template.yaml`, además del trigger nativo de EventBridge generado bajo la propiedad `Events` de la lambda, existe un recurso independiente `AWS::Events::Rule` apuntando al mismo destino, causando invocación doble garantizada desde el bus de eventos.

### Propuesta de Solucion
1. **Cambiar a Operaciones Atómicas:** Modificar el archivo `update_points.py` para usar `UpdateItem` en lugar de la secuencia `get_item` + `put_item`. Se debe emplear la cláusula `UpdateExpression="ADD points :val"`.
2. **Implementar Idempotencia:** Incluir en el evento un identificador único de transacción. Guardar este ID en DynamoDB y usar `ConditionExpression` para rechazar operaciones si el ID ya fue procesado.
3. **Corregir Infraestructura:** Eliminar el recurso duplicado `PurchaseRule` de tipo `AWS::Events::Rule` en el archivo `template.yaml`, conservando unicamente el trigger implícito en la definición de la Lambda.
4. **Mejorar Escalabilidad:** Eliminar `ReservedConcurrentExecutions: 1` del archivo `template.yaml` para permitir que el sistema escale naturalmente, dado que la escritura ahora estará protegida por las operaciones atómicas y condiciones de idempotencia.

# Token Usage

Total Tokens: 1261705
Prompt Tokens: 1241765
Input Tokens (non-cached): 375524
Response Tokens: 1826
Cached Tokens: 866241
Thoughts Tokens: 18114

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.751048
Cached Cost (USD):  $0.173248
Output Cost (USD):  $0.021912
Thoughts Cost (USD):$0.217368
Total Cost (USD):   $1.163576


# Execution time in seconds:

327
