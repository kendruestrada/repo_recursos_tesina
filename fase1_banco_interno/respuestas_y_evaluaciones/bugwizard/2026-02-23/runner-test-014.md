## Análisis del Sistema de Puntos de Fidelidad

### **Ticket:**
La aplicación registra de forma errónea los puntos de fidelidad de los usuarios, requiriendo identificación de la causa raíz mediante análisis de logs y código fuente.

### **Hallazgos en los logs:**

Después de analizar exhaustivamente los logs de CloudWatch, se identificaron los siguientes patrones:

1. **Múltiples invocaciones simultáneas**: Los logs muestran numerosas llamadas POST al endpoint `/points` con el mismo payload:
   ```json
   {"detail": {"user_id": "user_test_14", "amount": 500, "points_earned": 50}}
   ```

2. **Patrón temporal sospechoso**: Las invocaciones ocurren cada 5 minutos exactos (13:00:33, 13:05:27, 13:10:27, etc.), sugiriendo un proceso automatizado o de prueba.

3. **Ausencia de logs de error**: No se encontraron excepciones o errores explícitos en los logs analizados, lo que indica que las funciones se ejecutan "exitosamente" pero con resultados incorrectos.

4. **Diferentes fuentes IP**: Las llamadas provienen de múltiples IPs (44.204.93.133, 3.89.210.147, 13.220.192.48, 3.237.11.14), sugiriendo múltiples fuentes de eventos.

### **Relación con el código fuente:**

El análisis del código revela **condiciones de carrera críticas** en `update_points.py`:

```python
# PROBLEMA: Operación no atómica
response = table.get_item(Key={'user_id': user_id})
item = response.get('Item', {})
current_points = int(item.get('points', 0))

# Tiempo entre lectura y escritura permite condiciones de carrera
new_total = current_points + points_earned

table.put_item(
    Item={
        'user_id': user_id,
        'points': new_total
    }
)
```

**Problemas identificados:**

1. **Operación Read-Modify-Write no atómica**: Entre `get_item` y `put_item` pueden ocurrir múltiples actualizaciones concurrentes.

2. **Falta de control de concurrencia**: Sin `ReservedConcurrentExecutions: 1` efectivo para todas las fuentes de invocación.

3. **Múltiples puntos de entrada**: La función puede ser invocada tanto por EventBridge como por API Gateway, multiplicando las posibilidades de concurrencia.

### **Ejemplo de ejecución:**

**Escenario de condición de carrera:**

```
Estado inicial: user_test_14 tiene 100 puntos

Tiempo T1: Lambda A lee 100 puntos
Tiempo T2: Lambda B lee 100 puntos (mismo valor)
Tiempo T3: Lambda A calcula 100 + 50 = 150
Tiempo T4: Lambda B calcula 100 + 50 = 150
Tiempo T5: Lambda A escribe 150 puntos
Tiempo T6: Lambda B escribe 150 puntos (sobrescribe)

Resultado: 150 puntos (incorrecto)
Resultado esperado: 200 puntos
```

Con las múltiples invocaciones observadas en los logs, este escenario se repite constantemente.

### **Soluciones propuestas:**

#### **Solución 1: Actualización Atómica con DynamoDB (Recomendada)**

```python
def handler(event, context):
    # ... código de parsing existente ...
    
    try:
        # Usar UpdateItem con ADD para operación atómica
        response = table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='ADD points :points_to_add',
            ExpressionAttributeValues={':points_to_add': points_earned},
            ReturnValues='ALL_NEW'
        )
        
        new_total = response['Attributes']['points']
        
        print(f"Atomically updated points for {user_id}: {new_total}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                "message": f"Updated user {user_id} to {new_total} points",
                "user_id": user_id,
                "new_points": new_total
            })
        }
        
    except Exception as e:
        print(f"Error updating points: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({"error": "Failed to update points"})
        }
```

#### **Solución 2: Control de Concurrencia Optimista**

```python
def handler(event, context):
    # ... código de parsing existente ...
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Leer con versión
            response = table.get_item(Key={'user_id': user_id})
            item = response.get('Item', {})
            current_points = int(item.get('points', 0))
            version = item.get('version', 0)
            
            new_total = current_points + points_earned
            new_version = version + 1
            
            # Actualizar condicionalmente
            table.put_item(
                Item={
                    'user_id': user_id,
                    'points': new_total,
                    'version': new_version
                },
                ConditionExpression='attribute_not_exists(version) OR version = :current_version',
                ExpressionAttributeValues={':current_version': version}
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    "message": f"Updated user {user_id} to {new_total} points",
                    "user_id": user_id,
                    "new_points": new_total
                })
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    return {
                        'statusCode': 409,
                        'body': json.dumps({"error": "Concurrent modification detected"})
                    }
            raise
```

#### **Solución 3: Mejoras en la Configuración**

Actualizar `template.yaml`:

```yaml
UpdateLoyaltyPointsFunction:
  Type: AWS::Serverless::Function
  Properties:
    # ... propiedades existentes ...
    ReservedConcurrentExecutions: 1  # Forzar ejecución secuencial
    DeadLetterQueue:  # Manejar fallos
      Type: SQS
      TargetArn: !GetAtt PointsUpdateDLQ.Arn
```

### **Recomendación final:**

La **Solución 1 (Actualización Atómica)** es la más robusta ya que elimina completamente las condiciones de carrera utilizando las capacidades nativas de DynamoDB. Esta solución garantiza que las actualizaciones de puntos sean siempre consistentes, independientemente del número de invocaciones concurrentes.