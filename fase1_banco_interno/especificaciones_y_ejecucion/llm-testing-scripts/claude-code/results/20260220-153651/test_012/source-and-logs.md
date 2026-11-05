## Stock Negativo SKU-7821: Race Condition + Cache Viciado en Lambda

### Summary: El stock llega a -3 porque la validacion usa un cache de modulo obsoleto mientras la escritura usa el valor real de DynamoDB, permitiendo descuentos que superan el stock real disponible.

### Severity: Critical

---

### Root Cause Analysis

**Pasos para reproducir (segun los logs):**

Cada ciclo de ejecucion sigue exactamente este patron (observado en 13:00, 13:05, 13:10, 13:15):

| Paso | Usuario | `Estado DB antes` | `Visto en Cache` | `Estado DB despues` |
|------|---------|-------------------|------------------|---------------------|
| 1 | UserA | 5 | 5 | 2 (5-3) |
| 2 | UserB | 5 | 5 | 2 (5-3) — sobreescribe a UserA |
| 3 | UserC | **2** | **5** (VICIADO) | **-3** (2-5) |

**Evidencia del log (13:00:25 - 13:00:26):**
```
Estado DB antes: 2       ← UserC lee DB correctamente: stock = 2
Visto en Cache: 5        ← pero el cache aun dice 5 (nunca se actualizo)
Estado DB despues: -3    ← 2 - 5 = -3
```

**Expected vs. Actual:**
- Esperado: `cached_val < quantity` → bloquear la operacion (2 < 5 unidades solicitadas)
- Actual: `cached_val (5) >= quantity (5)` → pasa la validacion y escribe -3

---

**Ubicacion del bug: `inventory_handler/app.py`**

**Problema 1 — Cache de modulo persiste entre invocaciones calidas de Lambda (`app.py:10`):**
```python
internal_cache = {}  # persiste en el container reutilizado
```
Lambda reutiliza el entorno de ejecucion (warm start). El diccionario `internal_cache` sobrevive entre invocaciones dentro del mismo container. Se inicializa UNA vez con `stock=5` y **nunca se actualiza** despues de cada descuento.

**Problema 2 — El cache se escribe pero nunca se refresca despues del `put_item` (`app.py:22-42`):**
```python
if sku not in internal_cache:
    internal_cache[sku] = db_stock_antes   # se setea una sola vez
...
if cached_val >= quantity:     # validacion contra valor obsoleto
    new_stock = db_stock_antes - quantity  # escritura con valor fresco de DB
    table.put_item(...)        # actualiza DynamoDB
    # FALTA: internal_cache[sku] = new_stock
```
El cache queda en 5 incluso despues de que el stock en DB ya fue reducido a 2.

**Problema 3 — Race condition entre invocaciones concurrentes (`app.py:31-42`):**
UserA y UserB ejecutan simultaneamente, ambos leen `db_stock_antes=5`, ambos pasan la validacion, y ambos escriben `5-3=2`. La segunda escritura sobreescribe a la primera (no hay atomicidad). El stock deberia quedar en -1 por la doble deduccion, pero queda en 2. Esto "enmascara" la perdida y prepara el escenario para el stock negativo de UserC.

---

### Solucion

**1. Eliminar `internal_cache` y validar directamente contra `db_stock_antes`** (`app.py:31`):
```python
# Reemplazar:
if cached_val >= quantity:
# Por:
if db_stock_antes >= quantity:
```

**2. Actualizar el cache despues de cada escritura exitosa** si se requiere mantenerlo (`app.py:44`):
```python
internal_cache[sku] = new_stock
```

**3. Usar `update_item` con `ConditionExpression` para garantizar atomicidad** y eliminar la race condition entre invocaciones concurrentes:
```python
table.update_item(
    Key={'SKU': sku},
    UpdateExpression='SET stock = stock - :qty',
    ConditionExpression='stock >= :qty',
    ExpressionAttributeValues={':qty': quantity}
)
```
Esto hace que DynamoDB rechace la operacion si el stock es insuficiente en el momento exacto de la escritura, sin importar las lecturas previas ni el cache.

# Total cost USD

0.31052549999999995

# Execution time in seconds: 

58
