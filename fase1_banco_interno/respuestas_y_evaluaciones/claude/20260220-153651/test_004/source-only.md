Analizado el código fuente de ambas lambdas y el template. Se identificaron 3 bugs.

---

## Error de Despliegue e Integración: Sistema de Suscripciones

### Summary: El sistema presenta tres defectos que impiden el despliegue correcto y la ejecución del flujo async de permisos.

### Severity: Critical / High

---

### Root Cause Analysis

#### Bug 1 — `Timeout` como string en lugar de integer (Critical)

**Archivo:** `template.yaml:8`

```yaml
Globals:
  Function:
    Timeout: '{{resolve:ssm:/config/lambda/generic/timeout}}'
```

**Causa raiz:** SAM ejecuta su validación de schema **antes** de que CloudFormation resuelva las referencias dinámicas SSM. El schema de `Globals.Function.Timeout` espera un tipo `integer`. Al estar entre comillas simples, YAML lo interpreta como `string`, y SAM rechaza la plantilla en la fase de transformación con un error de tipo.

- **Esperado:** `Timeout: 30` (integer)
- **Actual:** `Timeout: '{{resolve:ssm:...}}'` (string) → falla en `sam deploy` / `sam validate`

---

#### Bug 2 — `StreamName` recibe un ARN completo en lugar del nombre del stream (Critical)

**Archivo:** `template.yaml:97-98`

```yaml
- DynamoDBStreamReadPolicy:
    TableName: !Ref SubscriptionsTable
    StreamName: !GetAtt SubscriptionsTable.StreamArn   # <-- BUG
```

**Causa raiz:** El policy template `DynamoDBStreamReadPolicy` de SAM construye internamente el ARN del recurso concatenando:
```
arn:aws:dynamodb:{Region}:{AccountId}:table/{TableName}/stream/{StreamName}
```
Al pasar el ARN completo como `StreamName`, el ARN resultante queda malformado:
```
arn:aws:dynamodb:us-east-1:123456789012:table/subscriptions/stream/arn:aws:dynamodb:us-east-1:...
```
Esto genera una política IAM que no matchea ningún recurso real, dejando a `lambda-b-sync-permissions` sin permisos para leer el stream de DynamoDB.

- **Esperado:** `StreamName: <identificador del stream>` (ej: timestamp del stream)
- **Actual:** `StreamName: arn:aws:dynamodb:...` → política IAM inválida → `AccessDeniedException` en runtime

---

#### Bug 3 — `requests.get()` sin timeout en Lambda B (High)

**Archivo:** `lambda_b/lambda_function.py:35`

```python
processor_url = os.environ.get("PROCESSOR_ENDPOINT_URL")
processor_response = requests.get(processor_url)   # sin timeout
```

**Causa raiz:** La llamada HTTP no tiene timeout configurado. Si el servicio externo no responde, Lambda B queda bloqueada hasta que el runtime la corte (timeout global del SSM). Dado que `ReservedConcurrentExecutions: 1`, ninguna otra invocación puede procesar el stream mientras tanto. Además, si `PROCESSOR_ENDPOINT_URL` es `None` (env var no resuelta), `requests.get(None)` lanza `MissingSchema` inmediatamente.

- **Esperado:** La llamada al endpoint externo tiene un límite de tiempo y falla rápido
- **Actual:** Bloqueo indefinido del procesamiento de permisos → timeout de Lambda → mensaje va a DLQ tras 2 reintentos

---

### Solution

**Bug 1:** Reemplazar la referencia dinámica SSM en `Globals` por un parámetro CloudFormation con tipo SSM:

```yaml
Parameters:
  LambdaTimeout:
    Type: AWS::SSM::Parameter::Value<Number>
    Default: /config/lambda/generic/timeout

Globals:
  Function:
    Timeout: !Ref LambdaTimeout
```

**Bug 2:** Reemplazar `StreamName` en `DynamoDBStreamReadPolicy` con el stream ARN directamente en una política custom, o usar solo el evento `Stream` de SAM que genera los permisos necesarios automáticamente. Alternativamente, eliminar el `DynamoDBStreamReadPolicy` redundante dado que SAM ya genera permisos para el event source mapping definido en `Events.Stream`.

**Bug 3:** Agregar timeout explícito a la llamada HTTP y validar la URL antes de usarla:

```python
processor_url = os.environ.get("PROCESSOR_ENDPOINT_URL")
if not processor_url:
    raise ValueError("PROCESSOR_ENDPOINT_URL is not configured")
processor_response = requests.get(processor_url, timeout=5)
```

# Total cost USD

0.30400024999999997

# Execution time in seconds: 

115
