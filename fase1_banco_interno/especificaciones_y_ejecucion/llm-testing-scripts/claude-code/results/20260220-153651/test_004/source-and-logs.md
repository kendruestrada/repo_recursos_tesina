Tengo toda la información necesaria del análisis. Los logs de lambda-a no tienen errores. El patrón en lambda-b es conclusivo. Procedo al informe final.

---

## [BUG] Lambda-B se bloquea en llamada HTTP externa antes de asignar permisos Cognito

### Summary: `requests.get(processor_url)` en lambda-b no tiene timeout configurado, lo que bloquea la ejecución hasta que Lambda expira, impidiendo que el usuario sea agregado al grupo `premium_users` de Cognito.

### Severity: Critical

---

### Root Cause Analysis

**Flujo esperado:**
1. Usuario se suscribe → lambda-a crea item en DynamoDB (`subscription_status: active`) → OK
2. DynamoDB Stream dispara lambda-b → lambda-b llama endpoint externo → agrega usuario a grupo Cognito `premium_users`

**Flujo real observado en logs:**

```
[INFO] Starting Cognito group assignment for user: canary-user-XXXXX
# --- SILENCIO: requests.get() cuelga sin timeout ---
REPORT RequestId: bb1d1ca9  Duration: 10000.00 ms  Status: timeout
```

El log `[INFO] Processor endpoint response: ...` de la línea 37 **nunca aparece**. Esto confirma que la función se congela en `requests.get(processor_url)` (línea 35) y Lambda expira antes de llegar a `cognito.admin_add_user_to_group()` (línea 41).

**Patrón de reintentos observado:**
- DynamoDB Streams reintenta automáticamente al detectar el fallo
- Cada reintento vuelve a colgar 10 segundos exactos → nuevo timeout
- Se registraron al menos **3 timeouts consecutivos por usuario** antes de que el stream avance
- El usuario queda **sin permisos Cognito**, aunque DynamoDB ya tiene `subscription_status: active`

**Steps to reproduce:**
1. Crear una suscripción con `user_id` válido via lambda-a
2. DynamoDB Stream dispara lambda-b
3. `PROCESSOR_ENDPOINT_URL` no responde o tarda más de 10s
4. Lambda-b expira → Cognito nunca recibe `admin_add_user_to_group`
5. Usuario ve suscripción activa en dashboard (DynamoDB OK) pero no accede a features premium (Cognito no actualizado)

**Expected vs. Actual:**

| | Esperado | Real |
|---|---|---|
| `requests.get()` | Responde y continúa | Cuelga indefinidamente |
| `admin_add_user_to_group` | Se ejecuta | Nunca alcanzado |
| Lambda duration | < 1000ms | 10000ms (timeout) |
| Cognito group | `premium_users` asignado | Sin asignación |

**Location del bug:**

`lambda_b/lambda_function.py:35` — llamada HTTP sin timeout

```python
# PROBLEMA: sin timeout, la llamada bloquea hasta que Lambda expira
processor_response = requests.get(processor_url)
```

Lambda-a no presenta errores (`filter_log_events` retornó vacío).

---

### Solution

**Corrección inmediata — agregar timeout en la llamada HTTP:**

```python
# lambda_b/lambda_function.py, línea 35
processor_response = requests.get(processor_url, timeout=5)
```

**Corrección estructural recomendada — mover la llamada HTTP fuera del camino crítico:**

La asignación al grupo Cognito no depende lógicamente de la respuesta del `PROCESSOR_ENDPOINT_URL`. Si el endpoint externo es un proceso auxiliar (notificación, telemetría, etc.), debe ejecutarse **después** de `admin_add_user_to_group`, o manejarse con `try/except` propio para que un fallo externo no impida la asignación de permisos:

```python
# lambda_b/lambda_function.py
# 1. Primero: operación crítica
cognito.admin_add_user_to_group(
    UserPoolId=user_pool_id, Username=user_id, GroupName=group_name
)
print(f"[SUCCESS] User {user_id} added to {group_name} group")

# 2. Luego: llamada auxiliar con timeout y manejo de error aislado
try:
    processor_response = requests.get(processor_url, timeout=5)
    print(f"[INFO] Processor endpoint response: {processor_response.text}")
except requests.exceptions.RequestException as e:
    print(f"[WARN] Processor endpoint call failed (non-critical): {str(e)}")
```

**Verificar además:**
- Que la variable de entorno `PROCESSOR_ENDPOINT_URL` apunte a un endpoint accesible desde la VPC/región donde corre lambda-b
- Revisar si `PROCESSOR_ENDPOINT_URL` está configurada en el `template.yml` y si el valor en el entorno de producción es correcto
- Considerar si lambda-b tiene acceso de red al endpoint (Security Groups, NAT Gateway si está en VPC privada)

# Total cost USD

0.439422

# Execution time in seconds: 

108
