## Circuit Breaker Invertido con Cascada Total de Servicios: Condicion de Recuperacion Invertida en EmailService

### Summary: La condicion de comparacion en el metodo `call` del CircuitBreaker esta invertida, causando que el circuito jamas recupere tras abrirse, bloqueando permanentemente EmailService y propagando el error en cascada hacia OrderProcessing y PaymentConfirmation.

### Severity: Critical

---

### Root Cause Analysis

**Flujo de ejecucion afectado:**

`PaymentConfirmation` → invoca → `OrderProcessing` → invoca → `EmailService`

Los tres servicios fallan porque los errores de `EmailService` se propagan sin absorcion hacia arriba en la cadena.

---

**Bug principal: condicion invertida en CircuitBreaker**
Archivo: `lambda/email-service/index.py`, linea 30

```python
# CODIGO ACTUAL (BUGGY)
if self.state == "OPEN":
    if time.time() < self.last_failure_time + self.recovery_timeout:
        # Entra aqui cuando el timeout AUN NO expiro -> Transiciona a HALF-OPEN (INCORRECTO)
        self.state = "HALF-OPEN"
    else:
        # Llega aqui cuando el timeout YA expiro -> Bloquea para siempre (INCORRECTO)
        raise Exception("Circuit breaker is OPEN - all requests blocked")
```

```python
# LOGICA CORRECTA
if self.state == "OPEN":
    if time.time() >= self.last_failure_time + self.recovery_timeout:
        # Timeout expiro: permitir un intento de recuperacion
        self.state = "HALF-OPEN"
    else:
        # Timeout aun activo: bloquear solicitudes
        raise Exception("Circuit breaker is OPEN - all requests blocked")
```

El operador `<` debe ser `>=`. Con la logica actual:
- Durante los primeros `recovery_timeout=5` segundos tras abrirse: transiciona a HALF-OPEN incorrectamente (permite requests que igualmente fallan)
- Pasados los 5 segundos: bloquea **permanentemente** toda solicitud — el circuito nunca puede recuperarse

---

**Steps to reproduce:**

1. SES lanza `ThrottlingException` (evidenciado en logs de OrderProcessingFunction y EmailServiceFunction)
2. El CircuitBreaker acumula `failure_count` hasta alcanzar `failure_threshold=5`
3. Estado cambia a `OPEN`, se registra `last_failure_time`
4. Pasados 5 segundos, la condicion invertida ejecuta el `raise Exception("Circuit breaker is OPEN")` en lugar de transicionar a `HALF-OPEN`
5. Todos los requests quedan bloqueados indefinidamente hasta un cold start del contenedor Lambda
6. El nuevo contenedor inicia con `failure_count=0`, pero vuelve a acumular fallas por SES throttling, reiniciando el ciclo

---

**Expected vs. Actual:**

| Escenario | Esperado | Actual |
|---|---|---|
| `time.time() >= last_failure_time + 5s` | Transicion a HALF-OPEN, intento de recuperacion | `raise Exception` — bloqueo permanente |
| `time.time() < last_failure_time + 5s` | Bloquear request (circuito abierto) | Transicion a HALF-OPEN (permite requests fallidos) |

---

**Evidencia en logs (CloudWatch):**

- `self.failure_count: 0` / `self.last_failure_time: None` — 18 ocurrencias: cold starts frescos, circuito en CLOSED
- `failure_count: 1→2→3→4→5` — acumulacion de fallas por `ThrottlingException` de SES
- `Transition to OPEN state (after 5 failures)` — 12 ocurrencias: apertura del circuito
- `Circuit breaker is OPEN - all requests blocked` — 503 en 24 ocurrencias: bloqueo permanente activado (post-5s)
- `ThrottlingException: Rate exceeded for Amazon SES` — 73 ocurrencias en OrderProcessing: causa raiz subyacente

---

**Causa contribuyente: `external_status_check()` puede aportar fallas adicionales**
Archivo: `lambda/email-service/index.py`, lineas 149-157

La funcion `send_email_via_ses` llama a `external_status_check()` antes de invocar SES. Si la URL `STATUS_CHECK_URL` falla o retorna un valor falsy, lanza un `ClientError` que tambien incrementa el `failure_count` del circuit breaker, acelerando la apertura del circuito.

---

**Causa contribuyente: `recovery_timeout=5` segundos es insuficiente**
Archivo: `lambda/email-service/index.py`, linea 58

```python
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=5)
```

5 segundos no es suficiente para que SES se recupere de un throttling. Incluso si la condicion fuera correcta, el circuito reabriria inmediatamente al reintentar contra un SES aun saturado.

---

### Solution

**1. Corregir la condicion invertida** en `lambda/email-service/index.py:30`:

```python
# Cambiar:
if time.time() < self.last_failure_time + self.recovery_timeout:
# Por:
if time.time() >= self.last_failure_time + self.recovery_timeout:
```

**2. Aumentar `recovery_timeout`** a un valor que permita la recuperacion real de SES (minimo 30-60 segundos):

```python
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
```

**3. Verificar el endpoint `STATUS_CHECK_URL`**: confirmar que la URL configurada en el stack CDK (`bw_test_007-stack.ts:30`) este operativa y retorne un valor truthy cuando el servicio es saludable. Un fallo en este endpoint cuenta como falla adicional en el circuit breaker.

**4. Revisar los limites de envio en Amazon SES**: el throttling de SES indica que se esta superando el rate limit configurado. Considerar solicitar un aumento de cuota o implementar un retry con backoff exponencial antes de que el circuit breaker contabilice la falla.

# Total cost USD

0.2815845

# Execution time in seconds: 

101
