## CORS Bypass con Credenciales: Lectura de sesion desde origen externo

### Summary: La API refleja dinamicamente el header `Origin` en `Access-Control-Allow-Origin` con `Access-Control-Allow-Credentials: true`, permitiendo que cualquier sitio externo lea datos de sesion autenticados.

### Severity: Critical

---

### Evidencia en logs

Los logs de CloudWatch muestran un patron repetitivo e inequivoco. Cada ciclo de 5 minutos registra **dos SecurityAudit**: uno del origen legitimo y uno de un sitio externo sospechoso. Ambos completan la ejecucion sin ningun bloqueo ni accion defensiva (`"action":"none"`).

```
origin: "https://test-020-frontendbucket.s3.amazonaws.com"  → origen legitimo
origin: "https://app-rewards-service.io"                    → origen externo NO autorizado
```

Ambos retornan HTTP 200 con duraciones normales (25-370 ms), lo que confirma que el sitio externo obtiene la respuesta completa, incluyendo datos de sesion de DynamoDB.

---

### Root Cause Analysis

**Pasos para reproducir**

1. Usuario legitimo abre el frontend en `test-020-frontendbucket.s3.amazonaws.com`, hace clic en "Iniciar Sesion" → la funcion activa `session_active = true` en DynamoDB para `userId: user_123`
2. Sitio malicioso (`app-rewards-service.io`) envia `GET /user/profile` con `Origin: https://app-rewards-service.io` y el mismo `Bearer` token (hardcodeado en `index.html`)
3. El servidor responde con `Access-Control-Allow-Origin: https://app-rewards-service.io` + `Access-Control-Allow-Credentials: true`
4. El navegador permite que el sitio externo lea la respuesta completa, incluyendo `sensitive_data` y `session_status`

**Esperado vs. Real**

| | Esperado | Real |
|---|---|---|
| Origenes permitidos | Solo `test-020-frontendbucket.s3.amazonaws.com` | Cualquier origen — el valor del header `Origin` de la request se refleja tal cual |
| Credenciales + ACAO dinamico | Bloqueado por spec CORS | Permitido: el servidor echa de vuelta el origen solicitado |

**Ubicacion del bug**

Dos archivos con defectos combinados que forman la vulnerabilidad:

**`src/src/handlers/profile_service.js` — lineas 46-53**
```javascript
const responseHeaders = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": origin,          // <-- refleja el Origin de la request
    "Access-Control-Allow-Credentials": "true",     // <-- permite cookies/auth headers
    ...
};
```
La variable `origin` proviene directamente del header de la request (`event.headers.origin || "*"`). Al combinarla con `Allow-Credentials: true`, se viola la restriccion CORS: el estandar prohibe `Allow-Credentials: true` con `Allow-Origin: *`, pero aqui se evita ese control usando un valor dinamico especifico en lugar del literal `"*"`.

**`template.yaml` — linea 27**
```yaml
Cors:
  AllowOrigin: "'*'"   # <-- API Gateway no filtra origenes antes de llegar al Lambda
```
El wildcard en API Gateway no restringe el trafico: permite que cualquier origen llegue al Lambda, donde el bug de reflejo se materializa.

**Vulnerabilidad secundaria — `profile_service.js` lineas 27-30**
```javascript
const payload = JSON.parse(Buffer.from(token.split(".")[1], "base64").toString());
userId = payload.sub;   // JWT decodificado SIN verificar firma
```
El token JWT no se valida criptograficamente. Un atacante puede forjar el campo `sub` para acceder al perfil de cualquier usuario. Ademas, el token esta hardcodeado en `src/web/index.html`, por lo que cualquier visitante del frontend puede extraerlo.

---

### Solution

**1. Corregir la logica CORS en `profile_service.js`**

Reemplazar el reflejo dinamico por una lista blanca explicita:

```javascript
const ALLOWED_ORIGINS = ["https://test-020-frontendbucket.s3.amazonaws.com"];

const corsOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];

const responseHeaders = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": corsOrigin,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Session-Action"
};
```

**2. Restringir `AllowOrigin` en `template.yaml`**

```yaml
Cors:
  AllowMethods: "'GET,OPTIONS'"
  AllowHeaders: "'Content-Type,Authorization,X-Session-Action'"
  AllowOrigin: "'https://test-020-frontendbucket.s3.amazonaws.com'"
```

**3. Implementar verificacion de firma JWT**

Usar una libreria como `jsonwebtoken` con la clave secreta o el JWKS del proveedor de identidad. El decode sin verificacion (`Buffer.from(..., "base64")`) no provee ninguna garantia de autenticidad.

**4. Agregar logica de bloqueo al `SecurityAudit`**

Cambiar `"action":"none"` por un bloqueo real cuando el origen no esta en la lista blanca, devolviendo HTTP 403 antes de consultar DynamoDB.

**5. No exponer `sensitive_data` en la respuesta del perfil**

El campo `sensitive_data: "BUGWIZARD_KEY_8822"` se devuelve directamente al cliente. Filtrar los campos sensibles antes de serializar la respuesta.

# Total cost USD

0.39718614999999996

# Execution time in seconds: 

94
