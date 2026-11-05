## Error en Circuit Breaker: Condicion de Transicion Invertida

### Summary: La condicion de tiempo en el metodo `call()` del `CircuitBreaker` esta invertida, lo que hace que el patron funcione al reves de lo esperado.

### Severity: Critical

---

### Root Cause Analysis

**Archivo afectado:** `lambda/email-service/index.py` — funcion `CircuitBreaker.call()`, linea 30.

**Logica esperada de un Circuit Breaker:**
| Estado | Condicion | Accion |
|--------|-----------|--------|
| OPEN | timeout NO ha transcurrido | Bloquear la solicitud |
| OPEN | timeout YA transcurrio | Pasar a HALF-OPEN y probar |
| HALF-OPEN | exito | Pasar a CLOSED |
| HALF-OPEN | fallo | Volver a OPEN |

**Logica actual (bugueada) — lineas 29-34:**

```python
if self.state == "OPEN":
    if time.time() < self.last_failure_time + self.recovery_timeout:
        self.state = "HALF-OPEN"   # BUG: permite paso cuando el timeout NO expiro
        print("Transition to HALF-OPEN state.")
    else:
        raise Exception("Circuit breaker is OPEN - all requests blocked")  # BUG: bloquea cuando el timeout YA expiro
```

La condicion `time.time() < self.last_failure_time + self.recovery_timeout` es `True` cuando el timeout **aun no ha transcurrido**, es decir, el circuito acaba de abrirse. En ese momento el codigo incorrecto **permite el paso** (transicion a HALF-OPEN). Cuando el timeout **ya transcurrio** (`else`), el codigo **bloquea permanentemente**.

**Resultado observable:**
1. El circuito abre tras 5 fallas.
2. Durante los proximos 5 segundos (`recovery_timeout`): sigue procesando solicitudes (sin proteccion alguna).
3. Pasados los 5 segundos: bloquea todas las solicitudes para siempre — el servicio jamas se recupera.

**Ejemplo de ejecucion con valores hipoteticos:**

```
last_failure_time = 1000.0
recovery_timeout  = 5
time.time()       = 1002.0  (2 segundos despues, timeout NO expiro)

Condicion: 1002.0 < 1000.0 + 5  =>  1002.0 < 1005.0  =>  True
Accion actual:    HALF-OPEN (permite solicitud)  ← INCORRECTO
Accion esperada:  raise Exception (bloquear)     ← CORRECTO
```

---

### Solution

Invertir el operador de comparacion en `lambda/email-service/index.py:30`:

```python
# Linea 30 - ANTES (bugueado)
if time.time() < self.last_failure_time + self.recovery_timeout:

# Linea 30 - DESPUES (correcto)
if time.time() >= self.last_failure_time + self.recovery_timeout:
```

Con el operador `>=` el flujo queda correcto:
- Mientras el timeout no expira (`<`): se lanza la excepcion y se bloquea.
- Cuando el timeout expira (`>=`): se transiciona a HALF-OPEN y se permite una solicitud de prueba.

# Total cost USD

0.329751

# Execution time in seconds: 

75
