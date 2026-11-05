## [Titulo]: Falta de manejo de excepciones en operación UpdateCommand de DynamoDB
### Resumen: La llamada asíncrona para actualizar el estado de la sesión en DynamoDB se encuentra fuera de un bloque de captura de errores, provocando caídas no controladas de la función.
### Severidad: High
### Analisis de causa raiz
- **Pasos para reproducir:**
  1. Enviar una petición HTTP a la API con un token JWT válido y el encabezado `X-Session-Action: ACTIVATE` (como lo hace el botón "Iniciar Sesion").
  2. Simular un fallo en la tabla de DynamoDB (por ejemplo, interrupción de red, timeout, políticas IAM insuficientes o estrangulamiento de peticiones).
  3. La función Lambda intentará ejecutar la actualización mediante `UpdateCommand`.
- **Esperado vs. Actual:**
  - **Esperado:** Cualquier error de la base de datos debería ser capturado para retornar una respuesta HTTP 500 estructurada, conservando los encabezados CORS correctos para el navegador.
  - **Actual:** Debido a que el `UpdateCommand` no está protegido por el bloque `try/catch` que se encuentra más abajo, cualquier error en esta operación genera una excepción de tipo `UnhandledPromiseRejection`. Esto hace que la ejecución de la Lambda se interrumpa abruptamente y API Gateway retorne un error genérico (502 Bad Gateway) sin los encabezados CORS esperados por el frontend.
- **Ubicacion del error:** `src/handlers/profile_service.js` (Función `exports.handler`, específicamente en la línea que ejecuta `await docClient.send(new UpdateCommand(...))`).
- **Logs relevantes:** Dado que es un análisis de código fuente puro, la evidencia estructural muestra que la palabra reservada `try` recién comienza después del bloque `if (sessionAction === 'ACTIVATE' ...)` que interactúa asíncronamente con DynamoDB.
### Propuesta de Solucion
1. Reubicar el bloque condicional que contiene el `UpdateCommand` hacia el interior del bloque `try/catch` principal existente.
2. Como alternativa, envolver el `UpdateCommand` en su propio bloque `try/catch`. Esto permitiría que, en caso de fallar la activación de la sesión, la función continúe y al menos recupere el perfil de usuario con el `GetCommand`.
3. (Opcional pero recomendado) Incorporar encadenamiento opcional (`event.headers?.origin`) en las primeras líneas del archivo para evitar caídas por `TypeError` cuando el objeto `headers` no esté presente (ej. invocaciones de prueba manuales).

# Token Usage

Total Tokens: 47382
Prompt Tokens: 27789
Input Tokens (non-cached): 11628
Response Tokens: 647
Cached Tokens: 16161
Thoughts Tokens: 18946

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.023256
Cached Cost (USD):  $0.003232
Output Cost (USD):  $0.007764
Thoughts Cost (USD):$0.227352
Total Cost (USD):   $0.261604


# Execution time in seconds:

251
