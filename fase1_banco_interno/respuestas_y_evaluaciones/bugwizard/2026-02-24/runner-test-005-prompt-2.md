## Análisis del Ticket de Soporte

**Ticket:** Las solicitudes de crédito quedan en estado 'pending' indefinidamente. El flujo esperado es: recibir solicitud → guardar estado pending → evaluar riesgo → actualizar estado final, pero el proceso se detiene después del primer paso.

## Hallazgos en los Logs

Analizando los logs de CloudWatch, se identifican los siguientes patrones críticos:

1. **Timeouts sistemáticos**: Todas las ejecuciones del lambda `CreditEvaluation` terminan con `Status: timeout` después de exactamente 10,000ms (10 segundos).

2. **Flujo incompleto**: Los logs muestran que:
   - ✅ Se recibe la solicitud correctamente
   - ✅ Se guarda en DynamoDB con status=pending
   - ❌ **NO hay evidencia de invocación exitosa al lambda RiskAnalysis**
   - ❌ **NO hay actualización posterior del estado**

3. **Ejemplos de timeout**:
```
START RequestId: 222aee86-0db0-4492-a225-286ca9630be1
lambda CreditEvaluation
body: {'credit_id': '123'}
Se guarda solicitud en dynamodb con status=pending
Registro 123 guardado con estado=pending
END RequestId: 222aee86-0db0-4492-a225-286ca9630be1
REPORT Duration: 10000.00 ms Status: timeout
```

## Relación con el Código Fuente

### Problema Principal en `CreditEvaluation` (src/credit/app.py)

El código muestra que después de guardar en DynamoDB, se intenta invocar el lambda `RiskAnalysis`:

```python
# invoca a RiskAnalysis para consultar a la tabla
response = lambda_client.invoke(
    FunctionName=RISK_LAMBDA_NAME,
    InvocationType="RequestResponse",  # ← SÍNCRONO
    Payload=json.dumps({"credit_id": credit_id}),
)
```

### Problema Identificado en `RiskAnalysis` (src/risk/app.py)

El lambda `RiskAnalysis` realiza una llamada HTTP síncrona que está causando el bloqueo:

```python
# llama al endpoint processor
print("Invocando endpoint processor")
processor_response = requests.get(PROCESSOR_URL)  # ← BLOQUEO AQUÍ
print("processor body:", processor_response.text)
```

**Causa raíz**: La llamada `requests.get(PROCESSOR_URL)` no tiene timeout configurado y está bloqueando indefinidamente, causando que el lambda `RiskAnalysis` nunca responda, lo que a su vez hace que `CreditEvaluation` espere hasta el timeout de 10 segundos.

## Ejemplo de Ejecución

**Flujo actual problemático:**
1. `CreditEvaluation` recibe `{'credit_id': '123'}`
2. Guarda en DynamoDB: `status = 'pending'`
3. Invoca `RiskAnalysis` síncronamente
4. `RiskAnalysis` ejecuta `requests.get(PROCESSOR_URL)` sin timeout
5. **BLOQUEO**: La llamada HTTP nunca retorna
6. `RiskAnalysis` nunca responde a `CreditEvaluation`
7. `CreditEvaluation` espera 10 segundos y hace timeout
8. **Resultado**: El registro queda en estado 'pending' para siempre

## Soluciones Propuestas

### Solución 1: Agregar Timeout a la Llamada HTTP (Inmediata)

```python
# En src/risk/app.py
import requests
from requests.exceptions import RequestException, Timeout

def lambda_handler(event, context):
    # ... código existente ...
    
    try:
        # Agregar timeout de 5 segundos
        processor_response = requests.get(PROCESSOR_URL, timeout=5)
        print("processor body:", processor_response.text)
        
        # Actualizar el estado basado en la respuesta
        # ... lógica de actualización ...
        
    except Timeout:
        print("Timeout al llamar al processor")
        return {"statusCode": 408, "body": json.dumps({"error": "Timeout del processor"})}
    except RequestException as e:
        print(f"Error en llamada al processor: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Error del processor"})}
```

### Solución 2: Implementar Actualización de Estado (Crítica)

El código actual no actualiza el estado después de la evaluación de riesgo. Agregar en `RiskAnalysis`:

```python
# Después de la llamada exitosa al processor
try:
    # Determinar nuevo estado basado en la respuesta del processor
    new_status = "approved" if processor_response.status_code == 200 else "rejected"
    
    # Actualizar el estado en DynamoDB
    table.update_item(
        Key={"credit_id": credit_id},
        UpdateExpression="SET #st = :status, updated_at = :now",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":status": new_status,
            ":now": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        },
    )
    
    return {"statusCode": 200, "body": json.dumps({
        "credit_id": credit_id,
        "status": new_status
    })}
    
except Exception as e:
    # En caso de error, marcar como failed
    table.update_item(
        Key={"credit_id": credit_id},
        UpdateExpression="SET #st = :status, updated_at = :now",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":status": "failed",
            ":now": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        },
    )
```

### Solución 3: Agregar Permisos DynamoDB (Configuración)

Actualizar `template.yaml` para dar permisos de escritura a `RiskAnalysisFunction`:

```yaml
RiskAnalysisFunction:
  Type: AWS::Serverless::Function
  Properties:
    # ... propiedades existentes ...
    Policies:
      - DynamoDBReadPolicy:
          TableName: !Ref CreditTable
      - DynamoDBWritePolicy:  # ← AGREGAR ESTO
          TableName: !Ref CreditTable
```

### Solución 4: Arquitectura Asíncrona (Recomendada a largo plazo)

Considerar cambiar a invocación asíncrona para evitar timeouts:

```python
# En CreditEvaluation, cambiar InvocationType
response = lambda_client.invoke(
    FunctionName=RISK_LAMBDA_NAME,
    InvocationType="Event",  # ← ASÍNCRONO
    Payload=json.dumps({"credit_id": credit_id}),
)
```

**Prioridad de implementación:**
1. **Inmediato**: Agregar timeout a requests.get()
2. **Crítico**: Implementar actualización de estado en RiskAnalysis
3. **Importante**: Agregar permisos DynamoDB
4. **Futuro**: Evaluar arquitectura asíncrona con SQS/SNS