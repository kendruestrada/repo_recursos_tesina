Tengo todos los elementos necesarios. Aquí está el análisis completo:

---

## [CORS-001]: Bypass de CORS por reflexion de Origin con credenciales habilitadas

### Summary:
El servidor refleja dinámicamente el header `Origin` de la solicitud como valor de `Access-Control-Allow-Origin` junto con `Access-Control-Allow-Credentials: true`, permitiendo que cualquier sitio externo realice solicitudes autenticadas y lea la respuesta con datos de sesion de DynamoDB.

### Severity: **Critical**

---

### Root Cause Analysis

**Pasos para reproducir:**
1. Desde `https://app-rewards-service.io` realizar un `GET /user/profile` con un header `Authorization: Bearer <jwt_forjado>` y `Origin: https://app-rewards-service.io`
2. El servidor responde con `Access-Control-Allow-Origin: https://app-rewards-service.io` + `Access-Control-Allow-Credentials: true`
3. El navegador permite que el sitio externo lea la respuesta, incluyendo `session_active` y datos del item en DynamoDB

**Expected vs Actual:**

| Condicion | Esperado | Actual |
|---|---|---|
| Origin `https://app-rewards-service.io` | Rechazado o sin `Access-Control-Allow-Credentials` | Aceptado, credenciales habilitadas |
| Validacion del JWT | Verificacion de firma criptografica | Solo decodifica base64, sin verificar firma |
| Activacion de sesion | Solo desde origenes autorizados | Cualquier origen puede enviar `X-Session-Action: ACTIVATE` |

**Ubicacion de los bugs:**

**Bug 1 - CORS por reflexion de Origin** (`src/handlers/profile_service.js:8` y `:52-53`):
```js
// Linea 8: acepta cualquier origen sin validar
const origin = event.headers.origin || event.headers.Origin || "*";

// Linea 52-53: refleja el origen y habilita credenciales - combinacion prohibida por CORS spec
"Access-Control-Allow-Origin": origin,
"Access-Control-Allow-Credentials": "true",
```
Cuando `Access-Control-Allow-Credentials` es `true`, el estandar CORS exige que `Access-Control-Allow-Origin` sea un origen especifico y en whitelist, nunca un valor dinamico/reflejado. Esto convierte cualquier origen malicioso en un origen "confiable".

**Bug 2 - JWT sin verificacion de firma** (`src/handlers/profile_service.js:28`):
```js
// Solo decodifica el payload en base64, NO verifica la firma
const payload = JSON.parse(Buffer.from(token.split(".")[1], "base64").toString());
userId = payload.sub;
```
No existe ninguna llamada a `jwt.verify()`. Un atacante puede construir un JWT con cualquier `sub` (p.ej. `userId: "admin"`) y el sistema lo aceptara como valido.

**Bug 3 - API Gateway con CORS wildcard** (`template.yaml:27`):
```yaml
AllowOrigin: "'*'"
```
El preflight OPTIONS de API Gateway tambien acepta cualquier origen.

---

**Evidencia en logs** (patron repetido en todas las invocaciones):

```json
{
  "event": "SecurityAudit",
  "metadata": {
    "origin": "https://app-rewards-service.io",  // origen externo sospechoso
    "path": "/user/profile",
    "action": "none"   // nunca se bloquea la solicitud
  }
}
```

Los logs confirman que `https://app-rewards-service.io` accede al endpoint de forma continua (cada 5 minutos, intercalado con el origen legitimo `test-020-frontendbucket.s3.amazonaws.com`) y en ningun registro se registra un bloqueo (`action` siempre es `"none"`).

---

### Solution

**1. Validar el Origin contra una whitelist** (`profile_service.js:8`):
```js
const ALLOWED_ORIGINS = ["https://test-020-frontendbucket.s3.amazonaws.com"];
const requestOrigin = event.headers.origin || event.headers.Origin;
const origin = ALLOWED_ORIGINS.includes(requestOrigin) ? requestOrigin : ALLOWED_ORIGINS[0];
```

**2. Verificar la firma del JWT** (`profile_service.js:28`): utilizar `jsonwebtoken` con `jwt.verify(token, SECRET_KEY)` en lugar de solo decodificar el payload en base64. La clave publica/secreta debe estar en una variable de entorno o en AWS Secrets Manager.

**3. Restringir el CORS en API Gateway** (`template.yaml:27`): cambiar `AllowOrigin: "'*'"` al origen especifico del frontend.

**4. Separar el endpoint de activacion de sesion**: el header `X-Session-Action: ACTIVATE` no deberia estar en el mismo endpoint GET de consulta. Debe ser un endpoint separado con autenticacion mas estricta.

# Total cost USD

0.33917375

# Execution time in seconds: 

59
