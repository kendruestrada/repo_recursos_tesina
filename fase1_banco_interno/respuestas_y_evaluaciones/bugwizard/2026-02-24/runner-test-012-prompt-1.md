## Análisis del Ticket de Soporte Técnico

### **Ticket:** 
El inventario del producto SKU-7821 muestra -3 unidades disponibles (stock negativo), lo cual es un estado inválido que indica un problema en la lógica de control de inventario.

### **Hallazgos en los logs:**

Analizando los logs de CloudWatch, se identifican múltiples patrones problemáticos:

1. **Condiciones de carrera concurrente**: Se observan múltiples ejecuciones simultáneas (UserA, UserB, UserC) que procesan el mismo SKU al mismo tiempo.

2. **Inconsistencia entre cache y base de datos**: Los logs muestran repetidamente:
   ```
   Estado DB antes: 5
   Visto en Cache: 5
   Estado DB despues: 2
   ```
   Y posteriormente:
   ```
   Estado DB antes: 5  
   Visto en Cache: 2  # Cache desactualizado
   ```

3. **Progresión hacia stock negativo**: Se observa la secuencia:
   - Stock inicial: 5
   - Después de transacciones: 2
   - Finalmente: -3

4. **Múltiples usuarios procesando simultáneamente**: Los logs muestran START RequestIds concurrentes para diferentes usuarios, indicando ejecuciones paralelas sin sincronización.

### **Relación con el código fuente:**

El problema radica en múltiples fallas críticas en `app.py`:

1. **Cache interno sin sincronización**:
   ```python
   internal_cache = {}
   
   if sku not in internal_cache:
       internal_cache[sku] = db_stock_antes
   
   cached_val = internal_cache[sku]  # Valor obsoleto
   ```

2. **Validación basada en cache obsoleto**:
   ```python
   if cached_val >= quantity:  # Usa cache desactualizado, no DB actual
   ```

3. **Lectura y escritura no atómica**:
   ```python
   # Lectura
   response = table.get_item(Key={'SKU': sku})
   db_stock_antes = int(item_db.get('stock', 0))
   
   # Delay que permite condiciones de carrera
   time.sleep(0.5)
   
   # Escritura basada en valor obsoleto
   new_stock = db_stock_antes - quantity
   ```

### **Ejemplo de ejecución:**

**Escenario de condición de carrera:**
```
Estado inicial: SKU-7821 = 5 unidades

T1: UserA lee DB (stock=5), cache=5, quantity=3
T2: UserB lee DB (stock=5), cache=5, quantity=3  
T3: UserC lee DB (stock=5), cache=5, quantity=5

T4: UserA valida (cache=5 >= 3) ✓, calcula new_stock = 5-3 = 2
T5: UserB valida (cache=5 >= 3) ✓, calcula new_stock = 5-3 = 2
T6: UserC valida (cache=5 >= 5) ✓, calcula new_stock = 5-5 = 0

T7: UserA escribe stock=2
T8: UserB escribe stock=2 (sobrescribe)
T9: UserC escribe stock=0 (sobrescribe)

Resultado: Stock final inconsistente, no refleja las 11 unidades vendidas
```

### **Soluciones propuestas:**

#### **Solución 1: Actualización atómica con DynamoDB**
```python
def lambda_handler(event, context):
    body = json.loads(event['body'])
    sku = body.get('sku')
    quantity = body.get('quantity')
    user_id = body.get('user_id')
    
    try:
        response = table.update_item(
            Key={'SKU': sku},
            UpdateExpression='SET stock = stock - :qty, last_updated_by = :user, updated_at = :time',
            ConditionExpression='stock >= :qty',
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
                "new_stock": response['Attributes']['stock']
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

#### **Solución 2: Eliminar cache interno problemático**
- Remover completamente `internal_cache = {}` 
- Realizar validaciones directamente contra la base de datos
- Usar operaciones atómicas de DynamoDB

#### **Solución 3: Implementar retry con backoff exponencial**
```python
import random
import time

def lambda_handler_with_retry(event, context, max_retries=3):
    for attempt in range(max_retries):
        try:
            return atomic_stock_update(event, context)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException' and attempt < max_retries - 1:
                time.sleep(0.1 * (2 ** attempt) + random.uniform(0, 0.1))
                continue
            raise
```

La causa raíz es la **falta de atomicidad en las operaciones de inventario** combinada con un **sistema de cache interno defectuoso** que permite condiciones de carrera, resultando en stock negativo cuando múltiples usuarios procesan el mismo SKU simultáneamente.