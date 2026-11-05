## Análisis del Sistema de Puntos de Fidelidad

### **Ticket:**
La aplicación registra de forma errónea los puntos de fidelidad de los usuarios, requiriendo identificación de la causa raíz mediante análisis de logs y código fuente.

### **Hallazgos en los logs:**
Tras analizar los logs de CloudWatch, se identifican los siguientes patrones problemáticos:

1. **Múltiples invocaciones simultáneas**: Los logs muestran numerosas llamadas POST al endpoint `/points` con el mismo payload:
   ```json
   {"detail": {"user_id": "user_test_14", "amount": 500, "points_earned": 50}}
   ```

2. **Frecuencia excesiva**: Las llamadas ocurren cada 5 minutos de forma sistemática desde múltiples IPs (3.92.138.23, 44.204.93.133, 3.237.11.14, etc.), sugiriendo un proceso automatizado descontrolado.

3. **Ausencia de logs de error**: No se observan excepciones o errores explícitos en los logs, lo que indica que el código se ejecuta "correctamente" pero con lógica defectuosa.

### **Relación con el código fuente:**

#### **Problema Principal - Falta de Idempotencia:**
El archivo `update_points.py` presenta una lógica de acumulación sin validaciones:

```python
# Líneas 42-48: Lógica problemática
response = table.get_item(Key={'user_id': user_id})
item = response.get('Item', {})
current_points = int(item.get('points', 0))
new_total = current_points + points_earned  # ← ACUMULACIÓN SIN CONTROL

table.put_item(
    Item={
        'user_id': user_id,
        'points': new_total
    }
)
```

#### **Problemas Identificados:**

1. **Sin validación de duplicados**: No existe mecanismo para prevenir el procesamiento múltiple del mismo evento.

2. **Configuración de concurrencia**: En `template.yaml` línea 44:
   ```yaml
   ReservedConcurrentExecutions: 1
   ```
   Aunque limita la concurrencia, no previene el procesamiento repetido de eventos idénticos.

3. **Doble trigger**: La función puede ser invocada tanto por EventBridge como por API Gateway, creando potenciales duplicaciones.

### **Ejemplo de ejecución:**

**Escenario problemático:**
```
Estado inicial: user_test_14 = 0 puntos

Evento 1 (13:00:33): +50 puntos → Total: 50
Evento 2 (13:00:34): +50 puntos → Total: 100  ← DUPLICADO
Evento 3 (13:05:27): +50 puntos → Total: 150  ← DUPLICADO
Evento 4 (13:10:27): +50 puntos → Total: 200  ← DUPLICADO
...

Resultado: user_test_14 acumula puntos incorrectamente
```

### **Soluciones propuestas:**

#### **Solución 1: Implementar Idempotencia con Transaction ID**
```python
import hashlib
from datetime import datetime

def handler(event, context):
    # Generar ID único basado en contenido del evento
    event_content = f"{user_id}_{points_earned}_{detail.get('amount', 0)}"
    transaction_id = hashlib.md5(event_content.encode()).hexdigest()
    
    # Verificar si ya fue procesado
    try:
        table.get_item(
            Key={'transaction_id': transaction_id},
            TableName='ProcessedTransactions'
        )
        return {'statusCode': 200, 'body': 'Already processed'}
    except:
        pass
    
    # Procesar y marcar como procesado
    # ... lógica existente ...
    
    # Registrar transacción
    transactions_table.put_item(
        Item={
            'transaction_id': transaction_id,
            'processed_at': datetime.utcnow().isoformat(),
            'user_id': user_id
        }
    )
```

#### **Solución 2: Usar DynamoDB Conditional Writes**
```python
def handler(event, context):
    # ... código existente hasta obtener current_points ...
    
    try:
        table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='ADD points :points',
            ConditionExpression='attribute_not_exists(last_transaction) OR last_transaction <> :tx_id',
            ExpressionAttributeValues={
                ':points': points_earned,
                ':tx_id': transaction_id
            }
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {'statusCode': 200, 'body': 'Duplicate transaction ignored'}
        raise
```

#### **Solución 3: Modificar la arquitectura EventBridge**
```yaml
# En template.yaml - Agregar filtro de contenido
PurchaseRule:
  Type: AWS::Events::Rule
  Properties:
    EventPattern:
      source: ["com.bugwizard.store"]
      detail-type: ["PurchaseCompleted"]
      detail:
        user_id: [{"exists": true}]
        amount: [{"numeric": [">", 0]}]
    # Agregar DeadLetterConfig para eventos fallidos
```

#### **Solución 4: Implementar Rate Limiting**
```python
import time
from boto3.dynamodb.conditions import Key

def handler(event, context):
    current_time = int(time.time())
    window_start = current_time - 300  # 5 minutos
    
    # Verificar eventos recientes
    recent_events = table.query(
        IndexName='UserTimeIndex',
        KeyConditionExpression=Key('user_id').eq(user_id) & 
                              Key('timestamp').between(window_start, current_time)
    )
    
    if recent_events['Count'] > 1:  # Máximo 1 evento por ventana
        return {'statusCode': 429, 'body': 'Rate limit exceeded'}
```

### **Recomendación prioritaria:**
Implementar la **Solución 1** (Idempotencia con Transaction ID) combinada con **Solución 2** (Conditional Writes) para garantizar que cada evento de compra se procese exactamente una vez, eliminando la acumulación incorrecta de puntos observada en los logs.