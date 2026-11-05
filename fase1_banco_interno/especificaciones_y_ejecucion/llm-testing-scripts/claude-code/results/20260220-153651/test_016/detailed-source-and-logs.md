## Deadlock en Transferencias Bidireccionales Concurrentes

### Summary: Dos transacciones concurrentes en sentidos opuestos (A→B y B→A) generan un deadlock circular porque `reserve_resource` usa un loop infinito sin timeout, causando que ambas Lambdas fallen por timeout y dejen los recursos bloqueados en DynamoDB.

### Severity: Critical

---

### Root Cause Analysis

**Patron observado en logs (`/aws/lambda/test-016-transfer-processor`)**

Todas las ejecuciones muestran exactamente el mismo patron, repetido cada 5 minutos:

```
13:00:22.865  TXN: aed5a330 | RES: A | PH: 1 | STATE: RESERVED    ← TXN A→B adquiere res:A
13:00:23.291  TXN: 4a451793 | RES: B | PH: 1 | STATE: RESERVED    ← TXN B→A adquiere res:B
13:00:39.370  TXN: aed5a330 | RES: B | PH: 2 | STATE: ATTEMPT     ← A→B intenta adquirir res:B (BLOQUEADA por 4a451793)
13:00:39.662  TXN: 4a451793 | RES: A | PH: 2 | STATE: ATTEMPT     ← B→A intenta adquirir res:A (BLOQUEADA por aed5a330)
13:01:22      REPORT ... Status: timeout                            ← Ambas Lambdas expiran (60s)
                                                                    ← Nunca aparece STATE: FINISH
```

Ninguna transferencia llega a completarse. El log de `acc-setup` es saludable (~300ms), por lo que el problema es exclusivo del procesador de transferencias.

**Ubicacion del bug: `resource_registry.py:13` y `transfer_funds.py:28-34`**

**Bug 1 — Loop infinito en `reserve_resource` (causa raiz del deadlock)**

```python
# resource_registry.py:13
while True:                          # SIN timeout ni limite de reintentos
    try:
        table.put_item(...)
        return True
    except ConditionalCheckFailedException:
        time.sleep(0.1)              # Espera eterna si el recurso no se libera
```

El deadlock circular se forma asi:

| Tiempo | TXN A→B | TXN B→A |
|--------|---------|---------|
| t+0    | Adquiere `res:A` | — |
| t+0.4  | — | Adquiere `res:B` |
| t+16   | Espera `res:B` (held by B→A) | Espera `res:A` (held by A→B) |
| t+60   | Lambda timeout | Lambda timeout |

**Bug 2 — Recursos no liberados al expirar la Lambda**

Cuando Lambda hace timeout, el bloque `except` de `transfer_funds.py:46-49` **nunca se ejecuta**. Los items quedan en DynamoDB con un TTL de 300 segundos:

```python
# resource_registry.py:11
ttl = int(time.time()) + 300   # Los locks quedan activos 5 minutos mas
```

Esto bloquea la siguiente ejecucion (5 minutos despues) que encuentra los recursos aun reservados.

**Bug 3 — Resultado de validacion ignorado (`transfer_funds.py:31`)**

```python
verify_settlement_window(source)   # El valor de retorno se descarta
```

La validacion de integridad de fondos nunca bloquea la transferencia si falla. Ademas, se ejecuta mientras se sostiene el lock de `res:{source}`, alargando la ventana de deadlock.

---

### Solution

**1. Agregar timeout en `reserve_resource` (correccion critica)**

```python
def reserve_resource(resource_key, tx_id, timeout_sec=10):
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            table.put_item(...)
            return True
        except ConditionalCheckFailedException:
            time.sleep(0.1)
    raise TimeoutError(f"Could not acquire lock for {resource_key}")
```

**2. Ordenar la adquisicion de locks por nombre de recurso para romper la circularidad**

```python
# transfer_funds.py - adquirir siempre en orden canonico (A antes que B)
first, second = sorted([f"res:{source}", f"res:{target}"])
reserve_resource(first, tx_id)
reserve_resource(second, tx_id)
```

Esto garantiza que dos transacciones opuestas siempre compitan por el mismo recurso primero, evitando el wait circular.

**3. Verificar el resultado de la validacion**

```python
# transfer_funds.py:31
if not verify_settlement_window(source):
    raise Exception("Settlement validation failed")
```

**4. Reducir el TTL de los locks al minimo operativo**

El TTL de 300s es excesivo dado el intervalo de 5 minutos entre ejecuciones. Reducirlo a 90s o al doble del timeout de la Lambda (120s) para que los locks huerfanos expiren antes del siguiente ciclo.

# Total cost USD

0.48998699999999995

# Execution time in seconds: 

63
