## Análisis del Ticket de Soporte Técnico

**Ticket:** Revisión de errores en logs e identificación de causa raíz en el código fuente del sistema de inventario.

## Hallazgos en los logs

Después de analizar exhaustivamente los logs de CloudWatch, se identifican los siguientes patrones problemáticos:

1. **Condiciones de carrera (Race Conditions):** Se observan múltiples ejecuciones concurrentes donde diferentes usuarios (UserA, UserB, UserC) acceden simultáneamente al mismo SKU.

2. **Inconsistencias en el estado del cache vs base de datos:**
   - Estado DB antes: 5, pero "Visto en Cache: 2" 
   - Estado DB antes: 5, pero "Visto en Cache: 5" (correcto)
   - Estas inconsistencias indican que el cache interno no se actualiza correctamente

3. **Stock negativo resultante:** Se observan casos donde el stock final es -3, lo que indica sobreventa del inventario.

4. **Patrón de ejecución problemático:**
   ```
   UserA: Estado DB antes: 5, Cache: 5 → Actualiza a 2
   UserB: Estado DB antes: 5, Cache: 2 → Actualiza a 2  
   UserC: Estado DB antes: 2, Cache: 5 → Actualiza a -3
   ```

## Relación con el código fuente

El problema radica en múltiples fallas arquitectónicas en `inventory_handler/app.py`:

### 1. **Cache global no sincronizado**
```python
internal_cache = {}  # Cache global compartido entre invocaciones
```
Este cache persiste entre invocaciones de Lambda pero no se actualiza cuando otros procesos modifican la base de datos.

### 2. **Lógica de validación incorrecta**
```python
if cached_val >= quantity:  # Valida contra cache obsoleto
    # Obtiene stock actual de DB
    new_stock = db_stock_antes - quantity  # Usa valor de DB, no de cache
```
La validación se hace contra el cache, pero el cálculo usa el valor real de la base de datos.

### 3. **Falta de actualización del cache**
```python
# Actualiza DB pero NO actualiza el cache
table.put_item(Item={...})
# internal_cache[sku] nunca se actualiza
```

### 4. **Ausencia de control de concurrencia**
No hay mecanismos para prevenir que múltiples Lambda functions modifiquen el mismo SKU simultáneamente.

## Ejemplo de ejecución problemática

**Escenario:** SKU con stock inicial = 5, quantity = 3

**Ejecución concurrente:**
1. **Lambda A:** Lee DB (5) → Cache[sku] = 5 → Valida (5 >= 3) ✓
2. **Lambda B:** Lee DB (5) → Cache ya existe (5) → Valida (5 >= 3) ✓  
3. **Lambda A:** Actualiza DB (5-3=2) → Cache sigue en 5
4. **Lambda B:** Actualiza DB (5-3=2) → Cache sigue en 5
5. **Lambda C:** Lee DB (2) → Cache sigue en 5 → Valida (5 >= 3) ✓ → Actualiza DB (2-3=-1)

**Resultado:** Stock negativo y sobreventa.

## Soluciones propuestas

### Solución 1: Eliminación del cache interno (Recomendada)
```python
def lambda_handler(event, context):
    body = json.loads(event['body'])
    sku = body.get('sku')
    quantity = body.get('quantity')
    user_id = body.get('user_id')
    
    # Usar transacciones DynamoDB para operaciones atómicas
    try:
        response = table.update_item(
            Key={'SKU': sku},
            UpdateExpression='SET stock = stock - :qty, last_updated_by = :user, updated_at = :time',
            ConditionExpression='stock >= :qty',  # Validación atómica
            ExpressionAttributeValues={
                ':qty': quantity,
                ':user': user_id,
                ':time': datetime.utcnow().isoformat()
            },
            ReturnValues='ALL_NEW'
        )
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Success",
                "stock_final": response['Attributes']['stock']
            })
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Insufficient stock"})
            }
        raise
```

### Solución 2: Cache distribuido con Redis/ElastiCache
```python
import redis

redis_client = redis.Redis(host=os.environ['REDIS_ENDPOINT'])

def lambda_handler(event, context):
    # Implementar cache distribuido con TTL corto
    # y invalidación explícita tras actualizaciones
```

### Solución 3: Optimistic Locking con DynamoDB
```python
# Usar atributo version para control de concurrencia optimista
UpdateExpression='SET stock = stock - :qty, version = version + :inc',
ConditionExpression='stock >= :qty AND version = :current_version'
```

**Recomendación:** Implementar la Solución 1 por su simplicidad y efectividad para resolver el problema de concurrencia y mantener la consistencia de datos.