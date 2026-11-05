## Análisis del Ticket de Soporte

**Ticket:** Algunas solicitudes de crédito quedan 'en proceso' indefinidamente

## Hallazgos en los logs

Al analizar los logs de CloudWatch, se identifican patrones críticos que revelan la causa raíz del problema:

### 1. **Timeouts sistemáticos en todas las ejecuciones**
```
REPORT RequestId: 222aee86-0db0-4492-a225-286ca9630be1	Duration: 10000.00 ms	Billed Duration: 10507 ms	Memory Size: 128 MB	Max Memory Used: 90 MB	Init Duration: 506.81 ms	Status: timeout
```

### 2. **Patrón de ejecución interrumpida**
Todas las ejecuciones siguen el mismo patrón:
- Se recibe la solicitud correctamente
- Se guarda en DynamoDB con status="pending" 
- **La ejecución se corta abruptamente por timeout antes de completar el flujo**

### 3. **Evidencia del flujo incompleto**
```
lambda CreditEvaluation
body: {'credit_id': '123'}
Se guarda solicitud en dynamodb con status=pending
Registro 123 guardado con estado=pending
END RequestId: 222aee86-0db0-4492-a225-286ca9630be1
```

**Observación crítica:** No hay logs de la función `RiskAnalysisFunction` siendo invocada, lo que indica que el timeout ocurre antes de llegar a esa etapa.

## Relación con el código fuente

### **Código afectado en `src/credit/app.py`:**

```python
# invoca a RiskAnalysis para consultar a la tabla
response = lambda_client.invoke(
    FunctionName=RISK_LAMBDA_NAME,
    InvocationType="RequestResponse",  # ← SINCRÓNICO
    Payload=json.dumps({"credit_id": credit_id}),
)
```

### **Código problemático en `src/risk/app.py`:**

```python
# llama al endpoint processor
print("Invocando endpoint processor")
processor_response = requests.get(PROCESSOR_URL)  # ← SIN TIMEOUT
print("processor body:", processor_response.text)
```

### **Configuración de timeout en `template.yaml`:**

```yaml
Globals:
  Function:
    Timeout: '{{resolve:ssm:/config/lambda/generic/timeout}}'  # Probablemente 10 segundos
```

## Ejemplo de ejecución

**Flujo actual (problemático):**

1. **CreditEvaluation** recibe solicitud → ✅ Funciona
2. Guarda en DynamoDB status="pending" → ✅ Funciona  
3. Invoca **RiskAnalysis** síncronamente → ⚠️ Inicia
4. **RiskAnalysis** hace `requests.get(PROCESSOR_URL)` → ❌ **Se cuelga aquí**
5. El endpoint externo no responde o es muy lento → ❌ **Timeout**
6. Lambda timeout (10s) → ❌ **Ejecución terminada**
7. **Status queda "pending" para siempre** → ❌ **Problema reportado**

## Soluciones propuestas

### **Solución 1: Implementar timeout en requests (Inmediata)**

```python
# En src/risk/app.py
import requests

def lambda_handler(event, context):
    # ... código existente ...
    
    try:
        print("Invocando endpoint processor")
        # Agregar timeout explícito
        processor_response = requests.get(PROCESSOR_URL, timeout=5)  # 5 segundos max
        print("processor body:", processor_response.text)
        
        # Actualizar status a "approved" o "rejected" según respuesta
        table.update_item(
            Key={"credit_id": credit_id},
            UpdateExpression="SET #st = :status, updated_at = :now",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":status": "approved",  # o lógica basada en processor_response
                ":now": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            },
        )
        
    except requests.exceptions.Timeout:
        # Manejar timeout del endpoint externo
        table.update_item(
            Key={"credit_id": credit_id},
            UpdateExpression="SET #st = :status, updated_at = :now",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":status": "failed",
                ":now": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            },
        )
        return {"statusCode": 408, "body": json.dumps({"error": "Timeout del servicio externo"})}
```

### **Solución 2: Arquitectura asíncrona (Recomendada)**

```python
# En src/credit/app.py - cambiar invocación a asíncrona
response = lambda_client.invoke(
    FunctionName=RISK_LAMBDA_NAME,
    InvocationType="Event",  # ← ASÍNCRONO
    Payload=json.dumps({"credit_id": credit_id}),
)

# Retornar inmediatamente
return {
    "statusCode": 202, 
    "body": json.dumps({"message": "Solicitud en proceso", "credit_id": credit_id})
}
```

### **Solución 3: Aumentar timeout de Lambda**

```yaml
# En template.yaml
Globals:
  Function:
    Timeout: 30  # Aumentar a 30 segundos
```

### **Solución 4: Implementar reintentos y manejo de errores**

```python
# En src/risk/app.py
import time
from datetime import datetime

def lambda_handler(event, context):
    # ... código existente ...
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            processor_response = requests.get(PROCESSOR_URL, timeout=3)
            # Si llega aquí, fue exitoso
            break
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                # Último intento fallido
                table.update_item(
                    Key={"credit_id": credit_id},
                    UpdateExpression="SET #st = :status, updated_at = :now",
                    ExpressionAttributeNames={"#st": "status"},
                    ExpressionAttributeValues={
                        ":status": "failed",
                        ":now": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    },
                )
                return {"statusCode": 408, "body": json.dumps({"error": "Servicio no disponible"})}
            time.sleep(1)  # Esperar 1 segundo antes del siguiente intento
```

## Recomendación final

**La causa raíz es la falta de timeout en la llamada HTTP externa**, combinada con una arquitectura síncrona que no maneja fallos. Se recomienda implementar las **Soluciones 1 y 2** en conjunto para resolver tanto el problema inmediato como mejorar la arquitectura a largo plazo.