## Stock Negativo SKU-7821: Race Condition por Cache Viciado + Escritura No Atómica

### Summary: El cache interno de Lambda retiene stock obsoleto y la verificacion se hace contra ese valor viciado mientras la deduccion se aplica sobre el stock real de DynamoDB, permitiendo que la operacion pase el guard y resulte en stock negativo.

### Severity: Critical

---

### Root Cause Analysis

**Patron repetido en logs (ciclos 18:35, 18:40, 18:45, 18:50, 18:55):**

```
[UserA] Visto en Cache: 5  | DB antes: 5  → DB despues: 2   (compra 3 unidades)
[UserB] Visto en Cache: 2  | DB antes: 5  → DB despues: 2   (concurrente con UserA)
[UserC] Visto en Cache: 5  | DB antes: 2  → DB despues: -3  (BUG)
```

**Ejecucion de UserC que produce -3:**

| Paso | Variable | Valor | Problema |
|------|----------|-------|---------|
| Lee DB | `db_stock_antes` | `2` | Stock real despues de compras anteriores |
| Lee cache | `cached_val` | `5` | Cache viciado, nunca actualizado |
| Guard check | `cached_val >= quantity` | `5 >= 5` = True | Pasa porque usa cache obsoleto |
| Calcula nuevo stock | `db_stock_antes - quantity` | `2 - 5 = -3` | Deduce del valor real |
| Escribe en DynamoDB | `stock = -3` | **NEGATIVO** | No hay restriccion |

**Bug 1 — Cache viciado a nivel de contenedor Lambda** (`app.py:10`, `app.py:22-25`):

```python
internal_cache = {}          # persiste entre invocaciones warm

if sku not in internal_cache:
    internal_cache[sku] = db_stock_antes   # se carga UNA sola vez, nunca se actualiza
```

`internal_cache` es una variable de modulo que sobrevive reutilizaciones del contenedor Lambda (warm start). El stock se cachea en la primera invocacion y **nunca se refresca**. El contenedor de UserC almaceno `5` al inicio; cuando se ejecuta de nuevo el stock real ya es `2` pero el cache sigue en `5`.

**Bug 2 — Guard y deduccion usan valores distintos** (`app.py:31`, `app.py:34`):

```python
if cached_val >= quantity:        # verifica contra cache (puede ser obsoleto)
    new_stock = db_stock_antes - quantity   # deduce del valor real de DB
```

El guard usa `cached_val` (viciado) pero la operacion usa `db_stock_antes` (real). Incluso si se corrigiera el cache, dos invocaciones concurrentes pueden leer el mismo `db_stock_antes` simultaneamente, pasar el check y ambas escribir una deduccion independiente sobre el mismo valor — race condition clasico TOCTOU.

**Pasos para reproducir:**
1. Stock inicial SKU-7821 = 5
2. UserA compra 3 unidades en contenedor A → stock queda en 2, cache de contenedor A = 5 (ya no importa)
3. Contenedor C habia cacheado 5 en una invocacion anterior
4. UserC solicita 5 unidades en contenedor C: cache=5, DB real=2
5. Check: `5 >= 5` pasa → escribe `2 - 5 = -3`

**Esperado:** Transaccion de UserC rechazada por stock insuficiente (solo 2 unidades disponibles).  
**Actual:** Transaccion aprobada, stock queda en -3.

**Ubicacion:** `inventory_handler/app.py` lineas 10, 22-25, 31, 34, 37-42.

---

### Solution

El cache en memoria de Lambda no es confiable para control de stock concurrente. La solucion correcta es eliminar el cache y usar una **escritura condicional atomica en DynamoDB** (`update_item` con `ConditionExpression`), que garantiza atomicidad sin race conditions:

```python
# Reemplazar el bloque de verificacion + put_item con:
try:
    table.update_item(
        Key={'SKU': sku},
        UpdateExpression='SET stock = stock - :q, last_updated_by = :u, updated_at = :t',
        ConditionExpression='stock >= :q',
        ExpressionAttributeValues={
            ':q': quantity,
            ':u': user_id,
            ':t': datetime.utcnow().isoformat()
        }
    )
    # exito
except table.meta.client.exceptions.ConditionalCheckFailedException:
    # stock insuficiente — leer valor actual y retornar 400 con stock real
```

Esto resuelve ambos bugs:
- Elimina el cache viciado por completo
- La condicion y la deduccion son atomicas en DynamoDB — no hay ventana de race condition entre check y write
- Si el stock es insuficiente, DynamoDB lanza `ConditionalCheckFailedException` antes de modificar nada

# Total cost USD

0.29868875

# Execution time in seconds: 

73
