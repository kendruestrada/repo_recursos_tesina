## Saga Pattern: Estado Inconsistente por Compensacion Incompleta

### Summary: La orden queda marcada como `completed` en DynamoDB aunque el saga falla, y la compensacion no revierte ese estado ni el cobro al cliente.

### Severity: Critical

---

### Root Cause Analysis

El flujo del saga tiene **tres bugs encadenados** que producen un estado irrecuperable en DynamoDB:

**Flujo de ejecucion normal:**
```
ChargePayment → UpdateInventory → SendToWarehouse (FALLA) 
    → CompensateInventory → CompensateChargePayment (FALLA)
        → SagaFailed
```

---

#### Bug 1 — Estado prematuro `completed` (causa raiz primaria)

**Archivo:** `src/update_inventory.py:23`

```python
UpdateExpression='SET #status = :status, inventory_updated = :updated',
ExpressionAttributeValues={
    ':status': 'completed',   # <-- BUG: orden marcada como completada en paso 2 de 4
    ':updated': True
}
```

`UpdateInventory` es el **paso 2 de 4**. En este punto el pago fue cobrado, pero el warehouse aun no fue notificado ni el email enviado. Marcar la orden como `completed` aqui es semanticamente incorrecto. El valor correcto deberia ser un estado intermedio como `inventory_updated` o `processing`.

El propio codigo lo confirma en la linea 28:
```python
print(f"Order status set to 'completed' (this is the bug!)")
```

---

#### Bug 2 — Compensacion no revierte el campo `status`

**Archivo:** `src/revert_inventory.py:16-22`

```python
table.update_item(
    Key={'order_id': order_id},
    UpdateExpression='SET inventory_updated = :updated',
    ExpressionAttributeValues={
        ':updated': False
    }
)
```

`RevertInventory` solo resetea `inventory_updated = False`. No revierte el campo `status` de `'completed'` a `'failed'` o `'cancelled'`. Resultado: la orden permanece en DynamoDB con `status = 'completed'` aunque el saga fallo.

---

#### Bug 3 — Reembolso siempre falla (429)

**Archivo:** `src/refund_payment.py:22`

```python
raise Exception("Payment Gateway Error: 429 Too Many Requests - Rate limit exceeded")
```

`RefundPayment` lanza excepcion incondicionalmente. El cobro al cliente nunca se revierte. El `Catch` del estado `CompensateChargePayment` en el ASL redirige a `SagaFailed`, pero el registro del pago en DynamoDB permanece con `payment_status = 'charged'`.

---

#### Estado final inconsistente en DynamoDB

| Campo | Valor esperado tras fallo | Valor real tras fallo |
|---|---|---|
| `status` | `failed` / `cancelled` | `completed` |
| `inventory_updated` | `False` | `False` |
| `payment_status` | `refunded` | `charged` |

---

### Ejecucion hipotetica

**Entrada:** `order_id = "abc-123"`, `amount = 150.0`

1. `ChargePayment` → DynamoDB: `payment_status = 'charged'`, `payment_id = 'uuid-xyz'`
2. `UpdateInventory` → DynamoDB: `status = 'completed'`, `inventory_updated = True` ← **Bug 1**
3. `SendToWarehouse` → lanza `503 Service Unavailable` → activa compensacion
4. `RevertInventory` → DynamoDB: `inventory_updated = False` — pero `status` sigue siendo `'completed'` ← **Bug 2**
5. `RefundPayment` → lanza `429 Too Many Requests` — pago nunca reembolsado ← **Bug 3**
6. Saga termina en `SagaFailed`

**Estado final del registro:** `{status: "completed", inventory_updated: false, payment_status: "charged"}` — orden marcada como completada, sin stock reservado y con cobro no reembolsado.

---

### Solution

**Fix 1** — `src/update_inventory.py:23`: cambiar el valor del status a un estado intermedio:
```python
':status': 'inventory_updated'  # en lugar de 'completed'
```

**Fix 2** — `src/revert_inventory.py`: agregar el reset del campo `status` en la compensacion:
```python
UpdateExpression='SET inventory_updated = :updated, #status = :status',
ExpressionAttributeNames={'#status': 'status'},
ExpressionAttributeValues={':updated': False, ':status': 'failed'}
```

**Fix 3** — `src/refund_payment.py`: implementar logica real de reembolso con manejo de reintentos para errores `429`, o bien configurar reintentos en el ASL del estado `CompensateChargePayment` (actualmente no tiene `Retry`).

**Fix adicional en el ASL** — `statemachine/order_saga.asl.json:63-74`: agregar `Retry` al estado `CompensateChargePayment` para tolerar errores transitorios del gateway de pagos:
```json
"Retry": [{"ErrorEquals": ["States.ALL"], "MaxAttempts": 3, "BackoffRate": 2}]
```

# Total cost USD

0.23274675

# Execution time in seconds: 

64
