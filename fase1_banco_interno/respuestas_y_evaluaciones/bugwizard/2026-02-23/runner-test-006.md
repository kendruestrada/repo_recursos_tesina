## Análisis del Ticket de Soporte

**Ticket:** Revisión de errores en logs e identificación de causa raíz en el código fuente del sistema de precios de productos.

## Hallazgos en los logs

### Errores Críticos Detectados:

1. **Inconsistencias de precio masivas** - Se detectaron múltiples casos donde el precio mostrado al usuario difiere significativamente del precio real en la base de datos:
   - PROD-834: Usuario vio $107, DB tiene $50 (diferencia: $57)
   - PROD-139: Usuario vio $195, DB tiene $69 (diferencia: $126) 
   - PROD-506: Usuario vio $166, DB tiene $65 (diferencia: $101)
   - PROD-671: Usuario vio $200, DB tiene $55 (diferencia: $145)

2. **Patrón de error consistente**:
   ```
   "Inconsistencia de precio detectada"
   "Checkout rechazado por inconsistencia de precio"
   ```

3. **Flujo de validación funcionando correctamente**: El sistema está detectando las inconsistencias y rechazando los checkouts como debe ser.

## Relación con el código fuente

### Causa Raíz Identificada:

El problema está en la **arquitectura de invalidación de caché**. Analizando el código:

#### 1. **ProductPricingFunction** (product_pricing/app.py):
```python
# Obtiene precio del cache Redis
cached_price = redis_client.get(cache_key)
if cached_price:
    # Retorna precio cacheado SIN validar si está actualizado
    return {"price": price, "source": "cache"}

# Solo consulta DB si NO hay cache
redis_client.setex(cache_key, CACHE_TTL, str(price))  # TTL de 3600 segundos (1 hora)
```

#### 2. **CacheInvalidationFunction** (cache_invalidation/app.py):
```python
# Se ejecuta por DynamoDB Stream DESPUÉS de cambios en DB
cache_key = f"price:{product_id}"
deleted = redis_client.delete(cache_key)
```

#### 3. **InventoryCheckFunction** (inventory_check/app.py):
```python
# SIEMPRE lee directamente de DynamoDB (NO usa cache)
response = table.get_item(Key={"productId": product_id})
db_price = float(product.get("price", 0))
```

### Problema Principal:

**Race Condition y Window de Inconsistencia:**

1. **UpdatePriceFunction** actualiza el precio en DynamoDB
2. **Existe un delay** hasta que el DynamoDB Stream dispara **CacheInvalidationFunction**
3. Durante este window, **ProductPricingFunction** sigue sirviendo precios obsoletos del cache
4. **InventoryCheckFunction** lee el precio actualizado de DB
5. **Resultado**: El usuario ve un precio (cache obsoleto) pero el checkout valida contra otro precio (DB actualizada)

## Ejemplo de ejecución

### Escenario problemático:
```
T0: PROD-834 tiene precio $50 en DB y cache
T1: Admin actualiza precio a $50 → $107 via UpdatePriceFunction
T2: DynamoDB actualizado con $107
T3: Usuario consulta precio → ProductPricingFunction retorna $107 (cache aún no invalidado)
T4: Usuario procede al checkout con $107
T5: DynamoDB Stream dispara CacheInvalidationFunction (TARDE)
T6: InventoryCheckFunction lee $50 de DB (precio anterior por error en actualización)
T7: Checkout rechazado: precio usuario ($107) ≠ precio DB ($50)
```

## Soluciones Propuestas

### Solución 1: Invalidación Proactiva (Recomendada)
```python
# En UpdatePriceFunction, agregar invalidación inmediata:
def lambda_handler(event, context):
    # ... actualizar DB ...
    
    # Invalidar cache INMEDIATAMENTE después de actualizar DB
    cache_key = f"price:{product_id}"
    redis_client.delete(cache_key)
    
    logger.info("Cache invalidado proactivamente", productId=product_id)
```

### Solución 2: Validación de Timestamp
```python
# En ProductPricingFunction, agregar validación de frescura:
def lambda_handler(event, context):
    cached_data = redis_client.hgetall(cache_key)
    if cached_data:
        cached_timestamp = float(cached_data.get('timestamp', 0))
        # Verificar si cache es muy viejo comparado con DB
        if time.time() - cached_timestamp > MAX_CACHE_AGE:
            redis_client.delete(cache_key)
            # Proceder a consultar DB
```

### Solución 3: Cache Write-Through
```python
# En UpdatePriceFunction, actualizar cache y DB simultáneamente:
def lambda_handler(event, context):
    # Actualizar DB
    table.update_item(...)
    
    # Actualizar cache inmediatamente con nuevo valor
    cache_key = f"price:{product_id}"
    redis_client.setex(cache_key, CACHE_TTL, str(new_price))
```

### Solución 4: Configuración de Red (Inmediata)
```yaml
# En template.yaml, reducir el BatchSize del DynamoDB Stream:
Events:
  DynamoDBStream:
    Properties:
      BatchSize: 1  # Cambiar de 10 a 1 para procesamiento más rápido
      MaximumBatchingWindowInSeconds: 0  # Procesar inmediatamente
```

La **Solución 1** es la más efectiva ya que elimina completamente el window de inconsistencia al invalidar el cache sincrónicamente con la actualización de la base de datos.