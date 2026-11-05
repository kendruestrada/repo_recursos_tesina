## Análisis del Sistema de Suscripciones

**Ticket:** El usuario ve su suscripción activa en el dashboard pero no puede acceder a funciones premium. El sistema debería guardar la suscripción en DynamoDB y luego sincronizar permisos en Cognito automáticamente.

## Hallazgos en los logs:

Después de analizar exhaustivamente los logs proporcionados, **no se encontraron errores, excepciones o fallos** en el sistema. Los logs muestran únicamente:

- Múltiples requests POST exitosos al endpoint `/subscription`
- Diferentes usuarios creando suscripciones premium (`canary-user-*` y `test-user-123`)
- Requests provenientes de diversas IPs y user agents (PostmanRuntime, python-urllib3)
- Todos los requests tienen estructura válida con `user_id` y `plan_type: "premium"`

**Observación crítica:** Los logs solo muestran las peticiones HTTP entrantes, pero **no contienen logs de ejecución de las funciones Lambda**, lo que impide ver si hay errores en el procesamiento interno.

## Relación con el código fuente:

### Lambda A (Creación de suscripción) - `lambda_a/lambda_function.py`:
✅ **Funcionamiento correcto:**
- Valida correctamente el `user_id`
- Crea el item en DynamoDB con `subscription_status: "active"`
- Incluye logging adecuado
- Manejo de errores implementado

### Lambda B (Sincronización de permisos) - `lambda_b/lambda_function.py`:
🔍 **Posibles puntos de falla identificados:**

1. **Dependencia externa no controlada:**
```python
processor_url = os.environ.get("PROCESSOR_ENDPOINT_URL")
processor_response = requests.get(processor_url)
```
- Si este endpoint falla, toda la función falla
- No hay timeout configurado
- No hay manejo de errores HTTP

2. **Usuario inexistente en Cognito:**
```python
cognito.admin_add_user_to_group(
    UserPoolId=user_pool_id, Username=user_id, GroupName=group_name
)
```
- Si el usuario no existe en Cognito, esta operación fallará
- No hay validación previa de existencia del usuario

3. **Configuración de reintentos limitada:**
```yaml
MaximumRetryAttempts: 2
```
- Solo 2 reintentos pueden ser insuficientes para fallos temporales

## Ejemplo de ejecución:

**Escenario de falla más probable:**

```python
# Usuario crea suscripción
user_id = "test-user-123"
# ✅ Lambda A ejecuta correctamente
# ✅ DynamoDB: subscription_status = "active"

# 🔄 DynamoDB Stream dispara Lambda B
# ❌ Falla en processor_response = requests.get(processor_url)
#     - Timeout del endpoint externo
#     - Endpoint devuelve 500/503
# ❌ Excepción no manejada → función falla
# 🔄 Reintentos (máximo 2)
# ❌ Después de 2 fallos → mensaje va a DLQ
# 🚫 Usuario nunca se agrega al grupo premium_users
```

## Soluciones propuestas:

### 1. **Solución inmediata - Mejorar manejo de errores:**
```python
def lambda_handler(event, context):
    for record in event["Records"]:
        if record["eventName"] == "INSERT":
            try:
                # ... código existente ...
                
                # Mejorar llamada al processor
                try:
                    processor_url = os.environ.get("PROCESSOR_ENDPOINT_URL")
                    processor_response = requests.get(processor_url, timeout=10)
                    processor_response.raise_for_status()
                except requests.RequestException as e:
                    print(f"[WARNING] Processor endpoint failed: {e}")
                    # Continuar sin fallar toda la función
                
                # Validar usuario existe antes de agregar al grupo
                try:
                    cognito.admin_get_user(UserPoolId=user_pool_id, Username=user_id)
                except cognito.exceptions.UserNotFoundException:
                    print(f"[ERROR] User {user_id} not found in Cognito")
                    return  # Skip this user
                
                # Agregar al grupo
                cognito.admin_add_user_to_group(...)
                
            except Exception as e:
                print(f"[ERROR] Failed to sync permissions: {str(e)}")
                raise
```

### 2. **Solución arquitectural - Separar responsabilidades:**
```yaml
# En template.yaml - Aumentar reintentos
MaximumRetryAttempts: 5

# Agregar variables de entorno para timeouts
Environment:
  Variables:
    PROCESSOR_TIMEOUT: "10"
    RETRY_DELAY: "5"
```

### 3. **Solución de monitoreo - Agregar CloudWatch Alarms:**
```yaml
# Alarm para DLQ
DLQAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: PermissionsSyncDLQ
    MetricName: ApproximateNumberOfVisibleMessages
    Namespace: AWS/SQS
    Statistic: Sum
    Threshold: 1
```

### 4. **Pruebas adicionales recomendadas:**
- Verificar logs de CloudWatch de ambas funciones Lambda
- Revisar métricas de DLQ para mensajes fallidos
- Validar que el endpoint `PROCESSOR_ENDPOINT_URL` esté disponible
- Confirmar que los usuarios existen en Cognito antes de crear suscripciones

**Causa raíz más probable:** La función Lambda B está fallando silenciosamente debido a dependencias externas (endpoint processor) o usuarios inexistentes en Cognito, impidiendo la sincronización de permisos.