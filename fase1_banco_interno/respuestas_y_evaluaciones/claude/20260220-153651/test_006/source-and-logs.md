Tengo todo lo necesario para el análisis completo. El diff del commit es el dato clave.

---

## Cache Stale: Invalidacion de cache ocurre despues de llamada a API externa bloqueante

### Summary
Cuando se actualiza el precio de un producto en DynamoDB, la cache de Redis no se invalida inmediatamente porque la funcion `CacheInvalidation` ejecuta una llamada HTTP bloqueante a una API externa **antes** de eliminar la clave en Redis, dejando una ventana de tiempo en la que los usuarios reciben el precio antiguo desde cache y el checkout los rechaza con "Precio manipulado o desactualizado".

### Severity: High

---

### Root Cause Analysis

**Flujo de ejecucion del sistema:**

```
UpdatePrice → DynamoDB → DynamoDB Stream → CacheInvalidation → Redis.delete()
                 ↑
          ProductPricing lee de aqui (fuente de verdad)

Usuario → ProductPricing → Redis (precio antiguo en cache) → Checkout → InventoryCheck → DynamoDB (precio nuevo) → RECHAZO
```

**Pasos para reproducir:**
1. Admin llama a `UpdatePriceFunction` para cambiar el precio de PROD-XXX de $91 a $55.
2. DynamoDB se actualiza inmediatamente.
3. DynamoDB Stream dispara `CacheInvalidationFunction`.
4. La funcion ejecuta `requests.get(PROCESSOR_API_URL)` — llamada HTTP sincrona/bloqueante.
5. **Durante el tiempo que dura esa llamada**, un usuario consulta el precio: `ProductPricingFunction` devuelve el precio antiguo ($91) desde Redis.
6. El usuario intenta hacer checkout enviando `price=91`.
7. `InventoryCheckFunction` consulta DynamoDB y obtiene el precio real $55.
8. `abs(91 - 55) = 36 > 0.01` → retorna `"Precio manipulado o desactualizado"`.
9. `CheckoutFunction` rechaza la compra con HTTP 400.

**Expected vs. Actual:**
- Esperado: el precio en Redis se invalida atomicamente al detectar el cambio en DynamoDB Stream, antes de cualquier operacion secundaria.
- Actual: la invalidacion de cache queda bloqueada por una llamada HTTP a API externa de duracion indeterminada.

**Ubicacion del bug:**

`cache_invalidation/app.py:41-50`

```python
# PROBLEMA: el delete ocurre DESPUES de la llamada bloqueante
try:
    response = requests.get(PROCESSOR_API_URL)   # <-- bloquea la ejecucion
    ...
except Exception as e:
    logger.error("Error llamando a API externa", error=str(e))

cache_key = f"price:{product_id}"
deleted = redis_client.delete(cache_key)          # <-- se ejecuta tarde
```

**Evidencia en logs** — `InventoryCheckFunction` registra multiples inconsistencias con diferencias grandes entre el precio servido por cache y el precio real en DB:

| productId | precioQueMostroCache | precioRealEnDB | diferencia |
|-----------|---------------------|----------------|------------|
| PROD-671 | 200 | 55.0 | 145.0 |
| PROD-073 | 181 | 62.0 | 119.0 |
| PROD-507 | 170 | 62.0 | 108.0 |
| PROD-544 | 193 | 91.0 | 102.0 |

Las diferencias son exactas a precios distintos (no ruido), lo que confirma que no es manipulacion real sino precio antiguo en cache.

**Historia del bug — commit `074a368`:**

El commit "Se elimina el sleep y se agrega endpoint de procesamiento" reemplaza `time.sleep(INVALIDATION_DELAY)` por `requests.get(PROCESSOR_API_URL)`. Ambas versiones producen el mismo efecto: una demora bloqueante antes del `redis_client.delete()`. El problema existia antes del commit con el sleep de 30 segundos y persiste con la llamada HTTP.

---

### Solution

Mover la invalidacion de cache **antes** de la llamada a la API externa en `cache_invalidation/app.py`. La eliminacion de la clave Redis debe ser la primera operacion critica; la llamada al endpoint externo es secundaria y no debe bloquearla.

```python
# cache_invalidation/app.py

        # CORRECTO: invalidar cache primero
        cache_key = f"price:{product_id}"
        deleted = redis_client.delete(cache_key)
        logger.info(
            "Cache invalidado", productId=product_id, cacheEliminado=bool(deleted)
        )

        # llamada a API externa como operacion secundaria, no bloquea la consistencia
        try:
            response = requests.get(PROCESSOR_API_URL)
            logger.info(
                "Llamada a API externa completada", statusCode=response.status_code
            )
        except Exception as e:
            logger.error("Error llamando a API externa", error=str(e))
```

Con este cambio, en cuanto DynamoDB Stream detecta el cambio de precio, Redis queda invalidado inmediatamente. Cualquier consulta subsiguiente a `ProductPricingFunction` hara un cache miss, ira a DynamoDB y obtendra el precio actualizado, eliminando la ventana de inconsistencia que provoca el rechazo en checkout.

# Total cost USD

0.40964425000000004

# Execution time in seconds: 

127
