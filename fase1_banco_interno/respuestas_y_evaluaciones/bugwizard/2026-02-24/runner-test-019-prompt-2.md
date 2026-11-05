## Análisis del Ticket de Soporte Técnico

**Ticket:** La aplicación de búsqueda de productos por categorías presenta lentitud significativa para ciertas categorías específicas, afectando el rendimiento del endpoint REST.

## Hallazgos en los logs

Analizando los logs de CloudWatch, se identifican los siguientes patrones críticos:

### 1. **Tiempos de ejecución extremadamente variables:**
- **Ejecuciones rápidas:** 7-35ms para la mayoría de requests
- **Ejecuciones lentas:** 400-2300ms para algunos requests
- **Cold starts prolongados:** 1000-1200ms de tiempo de inicialización

### 2. **Advertencias recurrentes sobre métricas:**
```
UserWarning: No application metrics to publish. The cold-start metric may be published if enabled. If application metrics should never be empty, consider using 'raise_on_empty_metrics'
```

### 3. **Patrón de degradación de rendimiento:**
- Los requests lentos aparecen frecuentemente después de períodos de inactividad
- Se observan múltiples cold starts consecutivos
- Algunos requests tardan más de 2 segundos en completarse

## Relación con el código fuente

### **Problema Principal: Lógica de paginación ineficiente**

En el archivo `app.py`, líneas 50-71, se identifica una implementación problemática:

```python
while True:
    response = table.query(**query_kwargs)
    all_items.extend(response.get("Items", []))

    if len(all_items) >= fetch_limit:
        break

    last_key = response.get("LastEvaluatedKey")
    if not last_key:
        break

    query_kwargs["ExclusiveStartKey"] = last_key
    query_kwargs["Limit"] = fetch_limit - len(all_items)
```

### **Problemas identificados:**

1. **Bucle infinito potencial:** El código puede ejecutar múltiples queries a DynamoDB hasta obtener el límite deseado
2. **Falta de control de tiempo:** No hay timeout para evitar ejecuciones prolongadas
3. **Ineficiencia en categorías con pocos elementos:** Para categorías con elementos dispersos, puede requerir múltiples scans
4. **Ausencia de índices optimizados:** La consulta se basa únicamente en `category_id`

## Ejemplo de ejecución

**Escenario problemático:**
- Categoría: "electronics" 
- Límite solicitado: 20 productos
- Productos disponibles en la categoría: 15 (distribuidos en múltiples particiones)

**Flujo de ejecución:**
1. Primera query: retorna 8 productos + LastEvaluatedKey
2. Segunda query: retorna 4 productos + LastEvaluatedKey  
3. Tercera query: retorna 3 productos + sin LastEvaluatedKey
4. Total: 3 queries a DynamoDB para obtener 15 productos

**Tiempo estimado:** 800-2000ms vs 20-50ms esperado

## Soluciones propuestas

### **Solución 1: Implementar timeout y límite de iteraciones**
```python
@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
@logger.inject_lambda_context
def lambda_handler(event, context):
    # ... código existente ...
    
    MAX_ITERATIONS = 5  # Límite de queries
    iteration_count = 0
    
    while iteration_count < MAX_ITERATIONS:
        response = table.query(**query_kwargs)
        all_items.extend(response.get("Items", []))
        iteration_count += 1

        if len(all_items) >= fetch_limit:
            break

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break

        query_kwargs["ExclusiveStartKey"] = last_key
        query_kwargs["Limit"] = min(fetch_limit - len(all_items), 100)
```

### **Solución 2: Optimizar la estrategia de consulta**
```python
# Usar un límite más alto en la primera consulta
initial_limit = min(limit * 2, 100)  # Obtener más elementos inicialmente
query_kwargs = {
    "KeyConditionExpression": Key("category_id").eq(category),
    "Limit": initial_limit,
}
```

### **Solución 3: Implementar caché para categorías frecuentes**
```python
import json
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_products(category, limit):
    # Implementar lógica de caché
    pass
```

### **Solución 4: Configurar Provisioned Concurrency**
En `template.yaml`:
```yaml
SearchProductsFunction:
  Type: AWS::Serverless::Function
  Properties:
    # ... propiedades existentes ...
    ProvisionedConcurrencyConfig:
      ProvisionedConcurrencyLevel: 2
```

### **Solución 5: Optimizar la tabla DynamoDB**
```yaml
ProductsTable:
  Type: AWS::DynamoDB::Table
  Properties:
    # ... propiedades existentes ...
    GlobalSecondaryIndexes:
      - IndexName: CategoryIndex
        KeySchema:
          - AttributeName: category_id
            KeyType: HASH
        Projection:
          ProjectionType: ALL
        BillingMode: PAY_PER_REQUEST
```

## Recomendación prioritaria

**Implementar la Solución 1 inmediatamente** para controlar los bucles infinitos, seguida de la **Solución 4** para reducir cold starts. Estas medidas deberían reducir los tiempos de respuesta de 2000ms a menos de 200ms para la mayoría de consultas.