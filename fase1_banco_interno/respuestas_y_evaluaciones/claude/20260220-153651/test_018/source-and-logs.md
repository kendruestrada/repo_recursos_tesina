Con toda la información recopilada, ya tengo el panorama completo. Aquí está el análisis:

---

## Bug: Falla en flujo de ordenes - warehouse y email no se ejecutan

### Summary: La función `SendToWarehouseFunction` lanza una excepción hardcodeada en cada invocación, interrumpiendo la saga antes de llegar al paso de email; adicionalmente `UpdateInventoryFunction` marca la orden como `'completed'` prematuramente.

### Severity: Critical

---

### Root Cause Analysis

**Flujo observado en logs (por orden de ejecución):**

```
TriggerOrder     -> OK  (saga iniciada correctamente)
ChargePayment    -> OK  (pago procesado correctamente)
UpdateInventory  -> OK* (inventario actualizado, pero con bug de estado)
SendToWarehouse  -> ERROR 503 en CADA ejecucion (nunca exitoso)
SendEmail        -> NUNCA invocado (0 registros en CloudWatch)
```

**Dos bugs identificados:**

---

**BUG 1 — Principal: `send_to_warehouse.py:13`**

El handler no tiene lógica real. Siempre lanza una excepción sin condición:

```python
# send_to_warehouse.py
raise Exception("Warehouse API Error: 503 Service Unavailable - System under maintenance")
```

Log confirmatorio (en cada orden, sin excepción):
```
[ERROR] Exception: Warehouse API Error: 503 Service Unavailable - System under maintenance
Traceback (most recent call last):
  File "/var/task/send_to_warehouse.py", line 13, in handler
    raise Exception("Warehouse API Error: 503 Service Unavailable...")
```

Esto hace que la Step Functions State Machine falle en ese paso, **interrumpiendo la saga antes de llegar a `SendConfirmationEmailFunction`**, lo que explica los 0 registros en el log group `/aws/lambda/SendConfirmationEmailFunction`.

---

**BUG 2 — Secundario: `update_inventory.py:23`**

La función marca la orden como `'completed'` antes de que el flujo haya terminado:

```python
# update_inventory.py - línea 23
':status': 'completed',   # <-- bug: el flujo aún no terminó
```

El propio log lo evidencia:
```
⚠️  Order status set to 'completed' (this is the bug!)
```

El estado correcto en este paso debería ser intermedio (ej. `'inventory_updated'` o `'processing'`), reservando `'completed'` para cuando toda la saga finalice exitosamente.

---

**Steps to reproduce:**
1. Enviar cualquier orden al endpoint (TriggerOrder).
2. El flujo ejecuta ChargePayment (OK) y UpdateInventory (OK con bug de estado).
3. Al llegar a SendToWarehouse, la función lanza la excepción 503 incondicionalmente.
4. La saga falla. SendConfirmationEmailFunction nunca es invocada.

**Expected vs Actual:**
- Esperado: `SendToWarehouse` envía la orden → `SendEmail` confirma al cliente → estado final `'completed'`.
- Actual: `SendToWarehouse` falla → saga interrumpida → sin email → estado en DynamoDB ya marcado como `'completed'` incorrectamente.

**Location:**
- `src/send_to_warehouse.py:13` — excepción hardcodeada incondicional.
- `src/update_inventory.py:23` — valor `'completed'` prematuro en el campo `status`.

---

### Solution

**Para BUG 1** (`send_to_warehouse.py`): Reemplazar el bloque hardcodeado por la llamada real a la API del warehouse. Si la indisponibilidad es temporal (mantenimiento), implementar un mecanismo de reintento (retry) en la definición de la State Machine de Step Functions, o manejar el error 503 con un estado de espera antes de relanzar.

**Para BUG 2** (`update_inventory.py:23`): Cambiar el valor del estado de `'completed'` a un valor intermedio como `'inventory_updated'`. El estado `'completed'` debe ser asignado únicamente por el último paso exitoso de la saga, o por una tarea de finalización dedicada en la State Machine.

# Total cost USD

0.9210360000000001

# Execution time in seconds: 

69
