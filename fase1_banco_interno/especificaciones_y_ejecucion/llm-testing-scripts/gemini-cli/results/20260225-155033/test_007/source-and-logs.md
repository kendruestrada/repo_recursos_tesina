## Fallo lógico en Circuit Breaker que bloquea peticiones de forma permanente
### Resumen: La condición de validación de tiempo en el patrón Circuit Breaker de la función EmailService está invertida, causando que el sistema quede bloqueado indefinidamente al finalizar el tiempo de recuperación.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir:
  1. Enviar una ráfaga de solicitudes de pago que superen el límite de envíos por segundo de Amazon SES.
  2. Amazon SES responderá con errores `ThrottlingException`.
  3. El `CircuitBreaker` en `EmailService` registrará los fallos. Al llegar a 5 fallos, cambiará su estado a `OPEN`.
  4. Esperar a que pase el periodo de recuperación de 5 segundos (`recovery_timeout`).
  5. Enviar una nueva solicitud de pago. La aplicación la rechazará sistemáticamente con el error "Circuit breaker is OPEN - all requests blocked" sin intentar procesarla ni recuperarse.

- Esperado vs. Actual:
  - Esperado: Estando el circuito en estado `OPEN`, si el tiempo actual es mayor al tiempo del último fallo más el tiempo de recuperación, el circuito debe cambiar a `HALF-OPEN` para permitir una petición de prueba y verificar si el servicio remoto ya está disponible.
  - Actual: La validación de tiempo utiliza el operador menor que (`<`). Esto provoca que el circuito permita peticiones erróneamente durante el periodo de enfriamiento y, por el contrario, bloquee todas las peticiones lanzando una excepción una vez que el tiempo de recuperación ha transcurrido, dejando la aplicación completamente caída de forma irreversible.

- Ubicacion del error (file/function):
  - Fichero: `lambda/email-service/index.py`
  - Función: Método `call` dentro de la clase `CircuitBreaker`

- Logs relevantes:
  - `EmailService response: {"statusCode": 504, "body": "{\"error\": \"An error occurred (ThrottlingException) when calling the SendEmail operation: Rate exceeded for Amazon SES\", \"circuitBreakerState\": \"CLOSED\", \"failureCount\": 4}"}`
  - `EmailService response: {"statusCode": 504, "body": "{\"error\": \"An error occurred (ThrottlingException) ...\", \"circuitBreakerState\": \"OPEN\", \"failureCount\": 5}"}`
  - `EmailService response: {"statusCode": 503, "body": "{\"error\": \"Circuit breaker is OPEN - all requests blocked\", \"circuitBreakerState\": \"OPEN\", \"failureCount\": 5}"}`

### Propuesta de Solucion
1. Corregir el operador lógico en el método `call` del `CircuitBreaker`. Se debe cambiar la condición a `if time.time() > self.last_failure_time + self.recovery_timeout:` para permitir la transición a `HALF-OPEN` en el momento adecuado.
2. Implementar un mecanismo de manejo de errores más resiliente frente a limitaciones de tasa (rate limits). Considerar el uso de reintentos con retraso exponencial (Exponential Backoff) al interactuar con SES, o bien, desacoplar el envío de correos utilizando un servicio de colas como Amazon SQS para que la confirmación de la orden no falle por un pico de tráfico en el envío de emails.

# Token Usage

Total Tokens: 88249
Prompt Tokens: 82041
Input Tokens (non-cached): 49564
Response Tokens: 951
Cached Tokens: 32477
Thoughts Tokens: 5257

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.099128
Cached Cost (USD):  $0.006495
Output Cost (USD):  $0.011412
Thoughts Cost (USD):$0.063084
Total Cost (USD):   $0.180119


# Execution time in seconds:

115
