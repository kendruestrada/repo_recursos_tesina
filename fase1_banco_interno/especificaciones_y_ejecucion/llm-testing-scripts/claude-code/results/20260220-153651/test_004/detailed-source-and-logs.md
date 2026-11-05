Con toda la información recopilada, tengo suficientes datos para producir el análisis completo.

---

## Timeout en llamada HTTP bloquea asignacion de permisos Cognito en Lambda B

### Summary: Lambda B falla sistematicamente por timeout en una llamada HTTP bloqueante (`requests.get`) que se ejecuta antes de `admin_add_user_to_group`, impidiendo que el usuario obtenga acceso premium en Cognito.

### Severity: Critical

---

### Root Cause Analysis

**Patron observado en los logs de `/aws/lambda/lambda-b-sync-permissions`:**

Cada ejecucion para un evento INSERT sigue este patron:
```
START RequestId: 2a2a973b-...
[INFO] Received DynamoDB Stream event with 1 records
[INFO] Processing permissions for user_id: canary-user-1771613402
[INFO] Subscription status: active
[INFO] Starting Cognito group assignment for user: canary-user-1771613402
  <-- silencio de 10 segundos exactos -->
REPORT ... Duration: 10000.00 ms ... Status: timeout
```

Los logs que NUNCA aparecen:
- `[INFO] Processor endpoint response: ...`
- `[INFO] Adding user X to group Y`
- `[SUCCESS] User X added to premium_users group`

Esto confirma que la funcion se cuelga justo despues del log "Starting Cognito group assignment", antes de ejecutar cualquier llamada a Cognito.

**Ubicacion del bug:** `lambda_b/lambda_function.py:35`

```python
# lambda_b/lambda_function.py:34-38
processor_url = os.environ.get("PROCESSOR_ENDPOINT_URL")
processor_response = requests.get(processor_url)   # <-- SE CUELGA AQUI, SIN TIMEOUT
print(f"[INFO] Processor endpoint response: {processor_response.text}")

# Esta linea NUNCA se alcanza:
cognito.admin_add_user_to_group(...)
```

**Flujo roto:**

| Paso | Esperado | Actual |
|---|---|---|
| 1. Recibir stream DynamoDB | OK | OK |
| 2. Validar `subscription_status == active` | OK | OK |
| 3. Llamar `PROCESSOR_ENDPOINT_URL` | Respuesta rapida, continuar | Cuelga indefinidamente (10s) |
| 4. Llamar `cognito.admin_add_user_to_group` | Agrega usuario al grupo premium | Nunca se ejecuta |
| 5. Log `[SUCCESS]` | Aparece en logs | Nunca aparece |

**Evidencia adicional del retry storm:**

El mismo `RequestId: 2a2a973b-...` aparece en 3 invocaciones distintas consecutivas (18:50:03, 18:50:14, 18:50:25). Esto ocurre porque `lambda_b/lambda_function.py:49` hace `raise` al capturar la excepcion de timeout, lo que devuelve el evento al DynamoDB Stream para reintento. Cada reintento falla identicamente.

**Ejecuciones exitosas (sin timeout):**

Se observan ejecuciones rapidas (~850ms) como `RequestId: 985243ce` que finalizan sin procesar permisos. Estas corresponden a eventos que NO son `INSERT` (MODIFY/REMOVE), por lo que el bloque `if record["eventName"] == "INSERT":` los omite y retornan directamente — lo cual explica por que Lambda B no esta completamente caida, solo falla en el camino critico.

---

### Solution

El problema es que `requests.get()` en la linea 35 no tiene parametro `timeout`, por lo que espera indefinidamente hasta que Lambda agota su tiempo de ejecucion (10s).

**Correccion en `lambda_b/lambda_function.py:35`:**

Agregar un timeout explicito a la llamada HTTP:

```python
# Antes (linea 35):
processor_response = requests.get(processor_url)

# Despues:
processor_response = requests.get(processor_url, timeout=5)
```

**Consideraciones adicionales a evaluar:**

1. **Orden de operaciones:** La llamada al `PROCESSOR_ENDPOINT_URL` esta ubicada ANTES de `admin_add_user_to_group`. Si el endpoint externo no es estrictamente necesario para asignar el grupo Cognito, deberia reubicarse despues o ejecutarse de forma asincrona para que no bloquee el flujo principal de permisos.

2. **Manejo del fallo del endpoint externo:** El `except` captura el timeout y hace `raise`, lo que reintenta todo el evento. Si el endpoint externo es opcional o tolerante a fallos, la logica deberia continuar hacia Cognito aunque falle, y solo propagar el error si Cognito falla.

3. **Variable `PROCESSOR_ENDPOINT_URL`:** Si la variable de entorno no esta configurada, `os.environ.get("PROCESSOR_ENDPOINT_URL")` retorna `None`, y `requests.get(None)` lanzaria un `MissingSchema` exception antes del timeout — agregar validacion de esta variable.

# Total cost USD

0.3252845000000001

# Execution time in seconds: 

76
