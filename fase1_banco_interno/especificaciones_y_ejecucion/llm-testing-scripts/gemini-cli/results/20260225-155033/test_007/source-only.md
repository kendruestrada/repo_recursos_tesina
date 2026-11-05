## [Titulo]: Bloqueo permanente por validación de tiempo invertida en el Circuit Breaker
### Resumen: La evaluación del tiempo de recuperación en la clase Circuit Breaker utiliza un operador invertido, provocando un estado de bloqueo irrecuperable en el servicio de correos.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir:
  1. Enviar múltiples peticiones de procesamiento de pago u orden que terminen en error en el servicio de correos hasta alcanzar el límite de fallos permitidos (5 fallos).
  2. En este punto el Circuit Breaker cambiará su estado a "OPEN".
  3. Esperar un periodo de tiempo superior al límite de recuperación configurado (5 segundos) sin emitir peticiones.
  4. Enviar una nueva petición; la ejecución fallará de forma incondicional.
- Esperado vs. Actual:
  El comportamiento esperado es que, al superar el tiempo de recuperación, el sistema cambie al estado "HALF-OPEN" y permita una petición de prueba para verificar si el servicio externo se ha estabilizado. El comportamiento actual permite peticiones de prueba inmediatamente después del fallo (ignorando el periodo de gracia) y, de forma crítica, bloquea permanentemente cualquier intento una vez que el tiempo de recuperación ha expirado, dejando al servicio de correos incapacitado sin posibilidad de recuperación autónoma.
- Ubicacion del error (file/function):
  Fichero: `lambda/email-service/index.py`
  Función: Clase `CircuitBreaker`, método `call`
- Logs relevantes:
  Si bien no se dispone de logs de ejecución en el escenario, los logs en AWS CloudWatch mostrarían el registro de la excepción "Circuit breaker is OPEN - all requests blocked" de forma sistemática y permanente en las peticiones que ingresen después de transcurrido el tiempo de `recovery_timeout`, originando respuestas HTTP 503 recurrentes en la cadena de llamadas de Lambdas.
### Propuesta de Solucion
Se debe ajustar la condicional lógica responsable de calcular el tiempo transcurrido desde el último fallo en la transición de "OPEN" a "HALF-OPEN". 

En el método `call` de la clase `CircuitBreaker`, es imperativo invertir el operador condicional. Se debe reemplazar el operador de menor que (`<`) por mayor que (`>`).

La línea a modificar sería:
`if time.time() < self.last_failure_time + self.recovery_timeout:`
Por su versión corregida:
`if time.time() > self.last_failure_time + self.recovery_timeout:`

Esto asegurará que el patrón rechace peticiones durante el tiempo estipulado y habilite el estado de prueba de forma correcta una vez finalizada la ventana de recuperación.

# Token Usage

Total Tokens: 20539
Prompt Tokens: 15385
Input Tokens (non-cached): 7289
Response Tokens: 604
Cached Tokens: 8096
Thoughts Tokens: 4550

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.014578
Cached Cost (USD):  $0.001619
Output Cost (USD):  $0.007248
Thoughts Cost (USD):$0.054600
Total Cost (USD):   $0.078045


# Execution time in seconds:

75
