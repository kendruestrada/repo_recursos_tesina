## Inconsistencia de Tipo en `credit_id` entre Lambdas

### Summary: El `credit_id` se almacena en DynamoDB como `String` pero se pasa a `RiskAnalysis` con el tipo original del JSON de entrada, causando un fallo al recuperar el registro.

### Severity: High

---

### Root Cause Analysis

**Pasos para reproducir:**
1. El cliente envía `POST /credit` con body `{"credit_id": 123}` (valor numérico).
2. `CreditEvaluation` convierte a string al guardar en DynamoDB (`str(credit_id)` → `"123"`).
3. `CreditEvaluation` invoca a `RiskAnalysis` pasando `credit_id` sin convertir (`123`, entero).
4. `RiskAnalysis` consulta DynamoDB con `credit_id = 123` (entero).
5. La tabla tiene `credit_id` definida como `AttributeType: S` (String) en `template.yaml:31`.
6. DynamoDB lanza `ValidationException: Type mismatch for key credit_id expected: S actual: N`.
7. `RiskAnalysis` captura la excepción y retorna `statusCode: 500`.

**Comportamiento esperado vs. actual:**

| Paso | Esperado | Actual |
|---|---|---|
| `get_item` en Risk | Encuentra el registro guardado | `ValidationException` o `Item not found` |
| Respuesta final | `statusCode: 200` con datos del crédito | `statusCode: 500` con error de tipo |

**Ubicacion del bug:**

- **`src/credit/app.py:35`** — El payload enviado a `RiskAnalysis` usa `credit_id` en su tipo original (puede ser `int` si el JSON lo envía como número):
  ```python
  Payload=json.dumps({"credit_id": credit_id}),   # <- sin str()
  ```

- **`src/risk/app.py:24`** — `RiskAnalysis` consulta DynamoDB sin normalizar el tipo:
  ```python
  response = table.get_item(Key={"credit_id": credit_id})  # <- sin str()
  ```

  Mientras que en `src/credit/app.py:21` el almacenamiento sí normaliza:
  ```python
  Key={"credit_id": str(credit_id)},  # <- con str()
  ```

---

### Solution

El tipo del `credit_id` debe ser consistente en todo el flujo. Hay dos puntos a corregir:

**1. `src/credit/app.py:35`** — Convertir a `str` al construir el payload para `RiskAnalysis`:
```python
# Antes
Payload=json.dumps({"credit_id": credit_id}),

# Despues
Payload=json.dumps({"credit_id": str(credit_id)}),
```

**2. `src/risk/app.py:24`** — Normalizar el tipo al consultar DynamoDB (defensa en profundidad):
```python
# Antes
response = table.get_item(Key={"credit_id": credit_id})

# Despues
response = table.get_item(Key={"credit_id": str(credit_id)})
```

La causa raiz esta en `src/credit/app.py:35`: la conversion `str()` se aplica al escribir en DynamoDB (`update_item`) pero no al construir el payload para la invocacion de la lambda `RiskAnalysis`. Esto crea una inconsistencia de tipos que causa `ValidationException` en DynamoDB (tabla con clave de tipo `S`) o un `404` si el tipo llegara a coincidir pero el valor no.

# Total cost USD

0.1647925

# Execution time in seconds: 

44
