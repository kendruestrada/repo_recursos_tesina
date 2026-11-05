## Autenticacion comprometida: JWT sin verificacion de firma y CORS bypass por reflexion de origen

### Summary: El sistema acepta tokens JWT sin verificar su firma y refleja el origin del request en el header CORS con credenciales habilitadas, permitiendo que cualquier origen y cualquier token forjado operen como usuarios validos.

### Severity: Critical

---

### Root Cause Analysis

**Bug 1 - JWT sin verificacion de firma**

- **Ubicacion:** `src/handlers/profile_service.js:28`
- **Flujo de ejecucion:**
  1. Se recibe el header `Authorization: Bearer <token>`
  2. El token se divide por `.` y se toma el segmento `[1]` (payload)
  3. Se hace `base64.decode` del payload y se extrae `payload.sub` como `userId`
  4. **Nunca se verifica la firma** del token contra ningun secreto o clave publica

```js
// linea 28 - solo decodifica, no verifica
const payload = JSON.parse(Buffer.from(token.split(".")[1], "base64").toString());
userId = payload.sub;
```

- **Esperado:** verificar la firma JWT con una clave secreta/publica antes de confiar en el payload
- **Actual:** cualquier JWT con cualquier `sub` es aceptado como identidad valida, incluso tokens forjados manualmente

- **Consecuencia directa:** el bloque de la linea 35-42 ejecuta un `UpdateCommand` en DynamoDB activando sesion para cualquier `userId` que el atacante coloque en el payload del token forjado

---

**Bug 2 - CORS bypass por reflexion de origen con credenciales**

- **Ubicacion:** `src/handlers/profile_service.js:8` y `52-53`

```js
// linea 8 - se toma el origen del request sin validacion
const origin = event.headers.origin || event.headers.Origin || "*";

// lineas 52-53 - se refleja directamente en la respuesta con credentials true
"Access-Control-Allow-Origin": origin,
"Access-Control-Allow-Credentials": "true",
```

- **Esperado:** `Access-Control-Allow-Origin` debe ser un valor fijo de origen(es) confiables; no se puede usar `*` junto con `Allow-Credentials: true`
- **Actual:** el servidor refleja cualquier origen recibido en la respuesta, habilitando credenciales para ese origen. Esto elude la proteccion del navegador (SOP) porque el browser acepta el origen reflejado como valido

- **Nota adicional en template.yaml:27:** El API Gateway tiene `AllowOrigin: "'*'"` a nivel de infraestructura, lo que agrava el problema

---

**Flujo de ataque combinado (ejemplo de ejecucion):**

1. Atacante construye un JWT forjado con payload `{"sub": "admin_user_id"}` y firma arbitraria
2. Envia request desde cualquier dominio: `GET /user/profile` con `Authorization: Bearer <jwt_forjado>` y `X-Session-Action: ACTIVATE`
3. El handler extrae `userId = "admin_user_id"` sin verificar firma
4. Ejecuta `UpdateCommand` activando `session_active = true` para ese usuario en DynamoDB
5. La respuesta incluye `Access-Control-Allow-Origin: <origen_del_atacante>` con `Credentials: true`, permitiendo que el script del atacante lea la respuesta completa

---

### Solution

**Bug 1 - Verificacion de JWT:**
Usar una libreria como `jsonwebtoken` para verificar la firma antes de extraer el `sub`. El secreto o la clave publica debe provenir de una variable de entorno o AWS Secrets Manager, nunca estar hardcodeado.

```js
const jwt = require("jsonwebtoken");
const payload = jwt.verify(token, process.env.JWT_SECRET);
userId = payload.sub;
```

**Bug 2 - CORS con lista blanca:**
Reemplazar la reflexion de origen por una validacion contra una lista de origenes permitidos. Solo retornar el header `Access-Control-Allow-Origin` si el origen esta en la lista; de lo contrario, omitirlo o retornar el origen base del sistema.

```js
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || "").split(",");
const allowedOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
"Access-Control-Allow-Origin": allowedOrigin,
```

Ademas, en `template.yaml:27` cambiar `AllowOrigin: "'*'"` al dominio especifico del frontend.

# Total cost USD

0.247785

# Execution time in seconds: 

55
