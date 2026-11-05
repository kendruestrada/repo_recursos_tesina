## [Titulo]: Falta de validación del código de estado HTTP en la respuesta del proveedor externo de pagos
### Resumen: El sistema marca todos los pagos como exitosos y los guarda en base de datos sin verificar si la llamada a la API externa de pagos fue realmente aprobada o rechazada.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir:
  1. El webhook recibe el evento y extrae el `transaction_id`.
  2. La función ejecuta un `fetch` (GET) al `externalPaymentServiceUrl` para consultar la transacción.
  3. El proveedor externo rechaza el pago (por ejemplo, fondos insuficientes) o no encuentra la operación, respondiendo con un código de error HTTP (ej. 400 Bad Request, 402 Payment Required o 404 Not Found).
  4. La función ignora totalmente si la llamada a `fetch` fue exitosa (no evalúa `response.ok` ni el cuerpo de la respuesta).
  5. El sistema procede a ejecutar `docClient.send(new PutCommand(...))` asignando de forma estática y forzosa `payment_status: "success"` y `order_status: "paid"`.
  6. Posteriormente la función llama a la URL de confirmación, revelando el error de forma pasiva.
- Esperado vs. Actual:
  - **Esperado**: Tras la invocación a la pasarela de pagos, el código debe comprobar que la respuesta HTTP exponga un éxito (ej. `response.ok === true`). En caso de fallo, debe registrar la transacción de forma consecuente (estado fallido o retenido) y no confirmar un pago irreal.
  - **Actual**: El sistema sobreescribe el estado transaccional local afirmando que se recibió un pago, creando una inconsistencia crítica de negocio donde el sistema cree que la orden está pagada, pero el proveedor externo no efectuó débito alguno.
- Ubicacion del error (file/function): `src/internal_services/SavePayment.js` (en la función `exports.handler`)
- Logs relevantes:
  - Tras guardar forzosamente el registro en base de datos (`INFO LOCAL_PAYMENT_PERSISTED`), el registro de logs de CloudWatch muestra sistemáticamente confirmaciones fallidas provenientes del proveedor: `INFO CONFIRMATION_RESPONSE { status: 404, statusText: 'Not Found' }`.
  - Existen trazas intermitentes por `TypeError: fetch failed` o `SocketError` (18:20:26.134Z). Estos cortan la ejecución de raíz. El problema real está en los errores semánticos u operativos devueltos con códigos HTTP válidos (4xx/5xx) los cuales la aplicación enruta al camino del éxito sin revisión previa.
- Ejemplo de ejecución para depuración:
  - **Entrada**: Recibe `transaction_id = TRX_CANARY_8eafd2`.
  - **Consulta Externa**: `fetch` retorna una respuesta HTTP 404 Not Found de la pasarela de pago.
  - **Inconsistencia Lógica**: Al no existir ninguna declaración condicional (ej. `if (!response.ok)`), la lambda asume pago consolidado, guarda `"success"` en base de datos e invoca el endpoint POST de confirmación.
  - **Confirmación final**: El servidor externo rechaza confirmar lo inexistente y devuelve `{ status: 404, statusText: 'Not Found' }`.
### Propuesta de Solucion
1. **Validar la Respuesta HTTP**: Inmediatamente después del bloque de `fetch` inicial, evaluar si `response.ok` es verdadero. 
2. **Inspección de Contrato de Pago**: Extraer y decodificar el cuerpo de la respuesta del proveedor (`await response.json()`) para corroborar el estado real aprobado en el servicio externo.
3. **Manejo Dinámico de Estados**: Alimentar la inserción a DynamoDB dinámicamente con el estado obtenido, reemplazando el `"success"` hardcodeado por la variable que represente fielmente la respuesta del banco/proveedor (`"success"`, `"failed"`, o `"pending"`).
4. **Cortocircuito**: Si el proveedor de pagos informa un rechazo definitivo, abortar el flujo normal y retornar la alerta pertinente al sistema y a los logs, evitando invocar innecesariamente el webhook de confirmación final.

# Token Usage

Total Tokens: 69354
Prompt Tokens: 64862
Input Tokens (non-cached): 48643
Response Tokens: 1025
Cached Tokens: 16219
Thoughts Tokens: 3467

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.097286
Cached Cost (USD):  $0.003244
Output Cost (USD):  $0.012300
Thoughts Cost (USD):$0.041604
Total Cost (USD):   $0.154434


# Execution time in seconds:

159
