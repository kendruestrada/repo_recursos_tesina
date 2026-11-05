## Bug Identificado: Pérdida de datos en actualización de puntos DynamoDB

### Summary: `update_points.py` usa `put_item` en lugar de `update_item`, sobreescribiendo completamente el item del usuario en DynamoDB y eliminando todos sus atributos excepto `user_id` y `points`.

### Severity: High

---

### Root Cause Analysis

**Pasos para reproducir:**
1. Un usuario con datos existentes en DynamoDB (ej: `name`, `email`, `tier`, `created_at`) realiza una compra.
2. `process_purchase.py` emite el evento `PurchaseCompleted` con `user_id` y `points_earned`.
3. `update_points.py` recibe el evento, consulta el item actual, calcula el nuevo total.
4. Ejecuta `table.put_item(...)` con solo `user_id` y `points`.

**Esperado vs. Actual:**

| | Esperado |
|---|---|
| **Esperado** | Solo el campo `points` se actualiza; el resto de atributos del usuario se conserva. |
| **Actual** | El item completo es reemplazado. Todos los atributos distintos de `user_id` y `points` son eliminados permanentemente. |

**Ubicacion del bug:** `src/update_points.py:53-58`

```python
# CODIGO ACTUAL - sobreescribe el item completo
table.put_item(
    Item={
        'user_id': user_id,
        'points': new_total   # todos los demas atributos se pierden
    }
)
```

La causa raiz es que `put_item` en DynamoDB realiza un **reemplazo total** del item. No es una operacion de merge parcial. Al construir el `Item` solo con `user_id` y `points`, se descartan todos los demas campos del registro del usuario.

---

### Solution

Reemplazar `put_item` con `update_item` usando una `UpdateExpression`, lo cual modifica unicamente el campo `points` sin afectar los demas atributos:

```python
table.update_item(
    Key={'user_id': user_id},
    UpdateExpression='SET points = :new_total',
    ExpressionAttributeValues={':new_total': new_total}
)
```

**Nota adicional:** En `process_purchase.py:42-44`, el objeto `response` de boto3 se incluye directamente dentro de `json.dumps()`. Aunque para `put_events` los valores son serializables en la mayoria de los casos, incluir `ResponseMetadata` en la respuesta al cliente expone informacion interna de la infraestructura AWS. Se recomienda excluirlo o filtrar solo los campos necesarios (`FailedEntryCount`, `Entries`).

# Total cost USD

0.22066675000000002

# Execution time in seconds: 

73
