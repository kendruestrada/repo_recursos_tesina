## Análisis del Ticket de Soporte Técnico

**Ticket:** La aplicación de búsqueda de productos por categorías presenta lentitud significativa para ciertas categorías específicas, afectando la experiencia del usuario.

## Hallazgos en los logs:

### 1. **Diferencias significativas en tiempos de respuesta por categoría:**

**Categoría "electronics" (lenta):**
- Duración promedio: 500-2300ms
- Ejemplos críticos:
  - `Duration: 2300.76 ms` (RequestId: c3bb2237-c15f-42c4-890f-9e60764f5685)
  - `Duration: 2304.86 ms` (RequestId: d9971414-2f02-4317-bdf0-da8243181799)
  - `Duration: 1821.51 ms` (RequestId: a06fc6bf-0d23-4946-aa1f-cd100cc63115)

**Categoría "books" (rápida):**
- Duración promedio: 7-35ms
- Ejemplos típicos:
  - `Duration: 7.42 ms` (RequestId: 938b7568-f1ef-40c3-b1a9-5ddcd62eb47c)
  - `Duration: 20.32 ms` (RequestId: 7437b3ac-c426-4840-ac15-e0acc0473f8c)
  - `Duration: 16.91 ms` (RequestId: f6db2412-4c1f-4d1c-b42f-20547bbb90a2)

### 2. **Patrón de comportamiento:**
- Las consultas para "electronics" muestran tiempos de ejecución hasta **300 veces más lentos** que "books"
- No se observan errores de timeout o excepciones, pero sí degradación severa del rendimiento

## Relación con el código fuente:

### **Problema identificado en el algoritmo de paginación:**

```python
# Líneas 49-71 en app.py - CÓDIGO PROBLEMÁTICO
while True:
    response = table.query(**query_kwargs)
    all_items.extend(response.get("Items", []))

    if len(all_items) >= fetch_limit:  # ❌ PROBLEMA AQUÍ
        break

    last_key = response.get("LastEvaluatedKey")
    if not last_key:
        break

    query_kwargs["ExclusiveStartKey"] = last_key
    query_kwargs["Limit"] = fetch_limit - len(all_items)
```

### **Causa raíz:**
El algoritmo continúa haciendo consultas a DynamoDB hasta obtener exactamente `fetch_limit` elementos, sin considerar que algunas categorías pueden tener **miles de productos**. Para categorías grandes como "electronics", esto resulta en:

1. **Múltiples consultas secuenciales** a DynamoDB
2. **Transferencia innecesaria de datos** desde la base de datos
3. **Procesamiento de elementos que luego se descartan**

## Ejemplo de ejecución:

**Escenario: Categoría "electronics" con 5000 productos, solicitando 20 elementos**

```python
# Iteración 1: DynamoDB retorna 1000 elementos (límite por defecto)
all_items = [1000 elementos]  # len(all_items) = 1000 >= 20 ✓

# Iteración 2: Se ejecuta otra consulta innecesariamente
response = table.query(KeyConditionExpression=Key("category_id").eq("electronics"), 
                      Limit=20, ExclusiveStartKey=last_key)
all_items.extend([otros 1000 elementos])  # len(all_items) = 2000

# El ciclo continúa hasta procesar miles de elementos
# Solo para retornar items[:20] al final
```

**Vs. Categoría "books" con 50 productos:**
```python
# Iteración 1: DynamoDB retorna 50 elementos
all_items = [50 elementos]  # len(all_items) = 50 >= 20 ✓
# Termina rápidamente
```

## Soluciones propuestas:

### **Solución 1: Optimización del límite de consulta (Recomendada)**
```python
@metrics.log_metrics
@tracer.capture_lambda_handler(capture_response=False)
@logger.inject_lambda_context
def lambda_handler(event, context):
    # ... código existente ...
    
    try:
        # ✅ SOLUCIÓN: Usar el límite real desde el inicio
        query_kwargs = {
            "KeyConditionExpression": Key("category_id").eq(category),
            "Limit": limit,  # Usar directamente el límite solicitado
        }

        response = table.query(**query_kwargs)
        items = response.get("Items", [])

        # Procesar solo los elementos necesarios
        safe_items = []
        for i in items:
            safe_item = i.copy()
            if "data" in safe_item:
                safe_item["data"] = "(payload hidden)"
            safe_items.append(safe_item)

        result = {
            "count": len(items),
            "category": category,
            "items": safe_items,
            "page": page,
            "has_more": "LastEvaluatedKey" in response  # Indicar si hay más datos
        }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result, cls=DecimalEncoder),
        }
    except Exception as e:
        # ... manejo de errores existente ...
```

### **Solución 2: Implementación de paginación real**
```python
# Para implementación futura con paginación verdadera
def lambda_handler(event, context):
    # ... código existente ...
    
    # Obtener token de paginación de la solicitud
    pagination_token = query_params.get("next_token")
    
    query_kwargs = {
        "KeyConditionExpression": Key("category_id").eq(category),
        "Limit": limit,
    }
    
    if pagination_token:
        # Decodificar el token de paginación
        query_kwargs["ExclusiveStartKey"] = json.loads(pagination_token)
    
    response = table.query(**query_kwargs)
    
    result = {
        "count": len(response.get("Items", [])),
        "category": category,
        "items": safe_items,
        "page": page,
    }
    
    # Incluir token para siguiente página si existe
    if "LastEvaluatedKey" in response:
        result["next_token"] = json.dumps(response["LastEvaluatedKey"], cls=DecimalEncoder)
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result, cls=DecimalEncoder),
    }
```

### **Beneficios esperados:**
- **Reducción del 95% en tiempo de respuesta** para categorías grandes
- **Menor consumo de RCU** en DynamoDB
- **Mejor experiencia de usuario** con respuestas consistentes
- **Escalabilidad mejorada** para el crecimiento futuro de datos

La implementación de la Solución 1 debería resolver inmediatamente el problema de lentitud reportado.