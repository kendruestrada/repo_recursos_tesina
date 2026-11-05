Con la evidencia recolectada de logs y código fuente, tengo suficiente información para determinar la causa raiz.

---

## Búsqueda de productos lenta para categoría `electronics`

### Summary: La categoría `electronics` tiene latencias de 700–900ms mientras que `books` responde en 13–25ms, debido a que se transfieren todos los atributos del item desde DynamoDB, incluyendo un campo `data` de gran tamaño que luego es descartado en la respuesta.

### Severity: High

---

### Root Cause Analysis

**Correlación de logs confirmada:**

| Categoria | Request ID (muestra) | Duration |
|-----------|---------------------|----------|
| `electronics` | `b85bc6bd` | 905 ms |
| `books` | `414500d6` | 21 ms |
| `electronics` | `0580f78e` | 761 ms |
| `books` | `acab5e2a` | 22 ms |
| `electronics` | `73246a28` | 824 ms |
| `books` | `8214095a` | 17 ms |

El patrón es **consistente en todas las invocaciones** durante el periodo completo observado.

**Pasos para reproducir:**
1. `GET /search?category=electronics` → ~800ms
2. `GET /search?category=books` → ~18ms

**Expected vs Actual:**
- Esperado: tiempos similares ya que ambas categorías usan el mismo índice primario (`category_id` como HASH key)
- Actual: `electronics` es ~40x más lento

**Ubicación del problema:** `product_service/app.py:51-74`

**Causa raíz — doble problema:**

**1. Sin `ProjectionExpression`: se leen todos los atributos incluido `data`**

```python
# app.py:53-56 — se consulta DynamoDB sin filtro de atributos
query_kwargs = {
    "KeyConditionExpression": Key("category_id").eq(category),
    "Limit": fetch_limit,
}
```

Los items de `electronics` contienen un campo `data` de gran tamaño. El código lo lee completamente desde DynamoDB y luego lo descarta:

```python
# app.py:79-80 — el campo data se lee pero se oculta inmediatamente
if "data" in safe_item:
    safe_item["data"] = "(payload hidden)"
```

**2. Paginación forzada por el límite de 1MB por llamada de DynamoDB**

DynamoDB impone un límite de **1MB por respuesta por llamada**. Si los items de `electronics` son grandes (ej. ~60KB c/u), con `Limit=20`:
- La primera llamada devuelve ~16 items y retorna `LastEvaluatedKey`
- El `while True` de `app.py:60` realiza llamadas adicionales para completar los 20 items
- Cada llamada de red adicional suma ~200-400ms de latencia

`books` tiene items pequeños → una sola llamada DynamoDB → 13-25ms.

---

### Solution

**Solución principal — agregar `ProjectionExpression` para excluir el campo `data`:**

```python
# product_service/app.py
query_kwargs = {
    "KeyConditionExpression": Key("category_id").eq(category),
    "Limit": fetch_limit,
    "ProjectionExpression": "category_id, product_id, #name, price, stock",
    "ExpressionAttributeNames": {"#name": "name"},  # 'name' es reserved word
}
```

Esto elimina la transferencia del campo `data` desde DynamoDB, reduciendo el tamaño de respuesta y evitando las paginaciones múltiples por límite de 1MB.

**Solución alternativa — Lazy loading del campo `data`:**
Si `data` se necesita en otro endpoint, separar la consulta en dos: una para metadatos (búsqueda/listado) y otra para el detalle completo del producto.

**Configuración de infraestructura a verificar** (`template.yaml`):
- La tabla usa `category_id` (HASH) + `product_id` (RANGE) sin GSI adicionales, lo cual es correcto para este patrón de acceso.
- No se requieren cambios en la infraestructura si se implementa `ProjectionExpression`.

# Total cost USD

0.6478570000000001

# Execution time in seconds: 

180
