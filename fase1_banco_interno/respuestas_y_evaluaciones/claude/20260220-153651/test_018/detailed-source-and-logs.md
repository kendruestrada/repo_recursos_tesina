Con la información recopilada tengo suficiente evidencia para identificar dos bugs distintos. Presento el análisis completo:

---

## [Bug #1]: Warehouse API siempre falla con excepción hardcodeada (503)

### Summary: `SendToWarehouseFunction` lanza una excepción incondicional simulando un error 503, bloqueando el flujo completo a partir de ese paso.

### Severity: Critical

### Root Cause Analysis

**Steps to reproduce:**
1. Enviar una orden a la API REST (endpoint TriggerOrder)
2. El flujo de Step Functions inicia: pago procesado correctamente, inventario actualizado
3. Al llegar a `SendToWarehouseFunction`, la función lanza siempre una excepción sin intentar ninguna llamada real

**Expected vs. Actual:**
- **Esperado:** la función envía la orden a la bodega y retorna `{'status': 'success'}`
- **Real:** lanza `Exception("Warehouse API Error: 503 Service Unavailable - System under maintenance")` en cada invocación sin excepción

**Location of the bug:**
- Archivo: `src/send_to_warehouse.py:13`
- Log confirmatorio (presente en **todas** las invocaciones):
  ```
  [ERROR] Exception: Warehouse API Error: 503 Service Unavailable - System under maintenance
  Traceback: File "/var/task/send_to_warehouse.py", line 13, in handler
      raise Exception("Warehouse API Error: 503 Service Unavailable - System under maintenance")
  ```

**Efecto en cadena:** como `SendToWarehouseFunction` siempre falla, Step Functions nunca avanza a `SendConfirmationEmailFunction`. Esto se confirma por los logs: el grupo `/aws/lambda/SendConfirmationEmailFunction` tiene **0 registros** (0 invocaciones).

### Solution

El `raise Exception` en la línea 13 de `send_to_warehouse.py` debe ser reemplazado por la lógica real de llamada a la API del almacén. Mientras el servicio externo esté en mantenimiento, se debe implementar un mecanismo de reintentos (por ejemplo, Step Functions `Retry`) o una ruta alternativa. El código actual ni siquiera intenta la llamada; la excepción es incondicional.

---

## [Bug #2]: `UpdateInventoryFunction` marca la orden como `'completed'` prematuramente

### Summary: El estado de la orden se establece en `'completed'` en DynamoDB al finalizar la actualización de inventario, cuando el flujo aún tiene dos pasos pendientes (bodega y email).

### Severity: High

### Root Cause Analysis

**Steps to reproduce:**
1. El flujo llega a `UpdateInventoryFunction` después del pago
2. La función actualiza el inventario y en la misma operación establece `status = 'completed'`
3. La orden queda marcada como completada en DynamoDB aunque no se ha enviado a bodega ni se ha notificado al cliente

**Expected vs. Actual:**
- **Esperado:** el estado intermedio debería ser algo como `'inventory_updated'` o `'processing'`; `'completed'` solo debería escribirse al finalizar exitosamente **todos** los pasos
- **Real:** `':status': 'completed'` se escribe en `src/update_inventory.py:23` antes de que el flujo termine

**Location of the bug:**
- Archivo: `src/update_inventory.py:23`
- El propio código lo señala con el print de la línea 28:
  ```python
  print(f"⚠️  Order status set to 'completed' (this is the bug!)")
  ```
- Confirmado en logs de `/aws/lambda/UpdateInventoryFunction` en **cada** ejecución:
  ```
  ⚠️  Order status set to 'completed' (this is the bug!)
  ```

### Solution

Cambiar el valor de `:status` en la `UpdateExpression` de `'completed'` a un estado intermedio apropiado (por ejemplo, `'inventory_updated'`). El estado `'completed'` debe ser escrito únicamente por el último paso del flujo (después de enviar el email de confirmación), o bien por un paso de finalización dedicado en la máquina de estados.

---

## Resumen del flujo real vs esperado

| Paso | Estado esperado | Estado real |
|---|---|---|
| TriggerOrder | Inicia ejecución | Correcto |
| ChargePayment | Pago procesado | Correcto |
| UpdateInventory | Estado `inventory_updated` | **Bug:** escribe `completed` |
| SendToWarehouse | Envio exitoso a bodega | **Bug:** excepción 503 hardcodeada, siempre falla |
| SendConfirmationEmail | Email enviado | **Nunca se ejecuta** (0 invocaciones) |

La causa raíz del síntoma reportado (sin confirmación al cliente y sin envio a bodega) es el **Bug #1** en `send_to_warehouse.py:13`. El **Bug #2** en `update_inventory.py:23` es un error de consistencia de datos que genera estados incorrectos en DynamoDB pero no bloquea directamente el flujo de Step Functions.

# Total cost USD

0.8753465

# Execution time in seconds: 

71
