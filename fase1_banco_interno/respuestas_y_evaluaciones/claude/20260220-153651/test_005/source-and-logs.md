Tengo toda la información necesaria para el diagnóstico completo.

---

## Lambda RiskAnalysis: Timeout en llamada HTTP a PROCESSOR_URL

### Summary: La lambda `RiskAnalysis` cuelga indefinidamente en `requests.get(PROCESSOR_URL)` sin timeout configurado, lo que provoca que todas las solicitudes queden permanentemente en estado `pending`.

### Severity: Critical

---

### Root Cause Analysis

**Patrón observado en los logs (100% de las invocaciones):**

```
lambda RiskAnalysis
event: {'credit_id': 'canary-credit-...'}
response dynamodb: {'Item': {'credit_id': '...', 'status': 'pending', ...}}
Invocando endpoint processor
[-- sin más logs --]
REPORT Duration: 10000.00 ms  Status: timeout
```

El mensaje `"processor body:"` **nunca aparece** en ninguna invocación. Esto confirma que `requests.get(PROCESSOR_URL)` nunca retorna.

**Flujo de ejecución:**

```
CreditEvaluation                      RiskAnalysis
      |                                     |
      |-- DynamoDB: status=pending          |
      |-- lambda.invoke(RiskAnalysis) ----->|
      |        (InvocationType=             |-- DynamoDB: get_item (OK)
      |         RequestResponse)            |-- requests.get(PROCESSOR_URL)  <-- CUELGA
      |                                     |
      |<-- timeout (10s) ------------------|<-- timeout (10s)
```

**Archivos y líneas afectadas:**

- `src/risk/app.py:37` — llamada HTTP sin timeout:
  ```python
  processor_response = requests.get(PROCESSOR_URL)  # sin timeout
  ```

- `src/credit/app.py:32-36` — invocación síncrona de RiskAnalysis:
  ```python
  response = lambda_client.invoke(
      FunctionName=RISK_LAMBDA_NAME,
      InvocationType="RequestResponse",  # espera la respuesta bloqueando
      ...
  )
  ```

**Pasos para reproducir:**
1. Enviar una solicitud de crédito a `CreditEvaluation`
2. `CreditEvaluation` guarda `status=pending` y llama a `RiskAnalysis` de forma síncrona
3. `RiskAnalysis` lee DynamoDB exitosamente, llega a `requests.get(PROCESSOR_URL)` y se bloquea
4. Ambas lambdas agotan su timeout de 10 segundos
5. El registro en DynamoDB permanece con `status=pending` para siempre

**Esperado vs. Real:**

| | Esperado | Real |
|---|---|---|
| `requests.get()` | Retorna respuesta del procesador | Cuelga sin retornar nunca |
| Estado final en DynamoDB | `approved` o `rejected` | `pending` (sin cambio) |
| Duración RiskAnalysis | < 10s | Exactamente 10000ms (timeout forzado) |

**Problema secundario:** Incluso si `PROCESSOR_URL` respondiera, ninguna de las dos lambdas actualiza el estado en DynamoDB a un valor final. `RiskAnalysis` (`src/risk/app.py:40`) retorna el `Item` tal como está (con `status=pending`) sin ejecutar ningún `update_item` posterior.

---

### Solution

**1. Agregar timeout a la llamada HTTP en `src/risk/app.py:37`:**
```python
processor_response = requests.get(PROCESSOR_URL, timeout=5)
```
Esto evita que la lambda quede colgada y permite manejar el error correctamente.

**2. Verificar que `PROCESSOR_URL` sea accesible** desde la VPC/subnet donde corre la lambda. El timeout consistente en el 100% de las invocaciones sugiere que el endpoint es inalcanzable (falla de red, DNS, segurity group, o servicio caído).

**3. Agregar actualización del estado en DynamoDB** luego de obtener la respuesta del procesador, de modo que el registro pase de `pending` a un estado final (`approved`/`rejected`/`failed`).

**4. Considerar cambiar `InvocationType` a `Event` (asíncrono)** en `src/credit/app.py:34` para que `CreditEvaluation` no quede bloqueada esperando a `RiskAnalysis`, o bien aumentar el timeout de la lambda a un valor mayor que el timeout de la llamada HTTP.

# Total cost USD

0.566478

# Execution time in seconds: 

63
