## [Titulo]: Envíos duplicados por reintentos de SQS debido a payload incorrecto
### Resumen: Un nombre de campo erróneo en el JSON de la solicitud HTTP provoca que la API externa devuelva error, forzando a la cola SQS a reintentar el mensaje 5 veces y enviando el correo en cada intento.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir
  1. Enviar una petición a la API de creación de órdenes para generar un mensaje en la cola SQS.
  2. La función `EmailSenderFunction` procesa el evento e intenta realizar una petición POST al servicio externo.
  3. En la petición POST, se construye el JSON y se envía la clave "email" en lugar de "customer_email".
  4. El servicio externo valida el esquema, no encuentra "customer_email" y responde con un error indicando campos faltantes (aunque el sistema procese el envío parcial y lo mande al cliente de todas formas).
  5. La función captura el estado de error (distinto de 200) y arroja una excepción general.
  6. Al generarse una excepción en la función, SQS no elimina el mensaje de la cola y automáticamente realiza reintentos. Esto ocurre hasta el límite configurado (`maxReceiveCount: 5`), desencadenando exactamente el mismo comportamiento 5 veces y provocando los 5 correos idénticos.
- Esperado vs. Actual
  - Esperado: La función debe enviar la propiedad correcta ("customer_email") en el payload. Al hacerlo, el servicio devuelve un estado 200 OK, la ejecución finaliza con éxito y SQS retira el mensaje, logrando que el cliente reciba solo un correo.
  - Actual: Se envía la propiedad "email" en el payload, generando una respuesta de error de validación en la API. La función falla deliberadamente con una excepción, SQS detecta el fallo y repite la ejecución 5 veces consecutivas según su configuración, saturando de correos al cliente.
- Ubicacion del error (file/function)
  - email_sender/app.py / lambda_handler
- Logs relevantes
  - `Orden recibida de SQS: 67d12459-a8b7-49a1-8590-ff58c8345359`
  - `Error al enviar correo para la orden 67d12459-a8b7-49a1-8590-ff58c8345359: {"message": "Missing required fields: order_id, customer_email, amount"}`
  - `[ERROR] Exception: Error al enviar correo`
  - `Traceback (most recent call last): File "/var/task/app.py", line 27, in lambda_handler raise Exception("Error al enviar correo")`
### Propuesta de Solucion
Actualizar la construcción del JSON de la llamada HTTP mediante la librería `requests` en el archivo `email_sender/app.py`. Es indispensable cambiar el nombre de la clave `"email": email` por `"customer_email": email`, acoplándose correctamente al esquema esperado por el servicio de notificaciones. Con este ajuste, el servicio responderá con el código 200, logrando un término de ejecución exitoso en la función que prevenga los bucles de reintentos sobre la cola SQS. No se deben implementar estos cambios en esta etapa, según las directivas establecidas.

# Token Usage

Total Tokens: 209975
Prompt Tokens: 200999
Input Tokens (non-cached): 95074
Response Tokens: 1046
Cached Tokens: 105925
Thoughts Tokens: 7930

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.190148
Cached Cost (USD):  $0.021185
Output Cost (USD):  $0.012552
Thoughts Cost (USD):$0.095160
Total Cost (USD):   $0.319045


# Execution time in seconds:

158
