## Análisis del Ticket de Seguridad

**Ticket:** El equipo de ciberseguridad ha reportado que la información de la sesión se puede obtener desde sitios sospechosos externos en una aplicación que valida sesiones activas de usuarios en base de datos.

## Hallazgos en los logs

Analizando los logs de CloudWatch, se identifican múltiples patrones preocupantes:

1. **Accesos desde dominios sospechosos:**
   ```
   "origin":"https://app-rewards-service.io"
   ```
   Este dominio aparece consistentemente en los logs y no parece ser el dominio legítimo de la aplicación.

2. **Patrón de acceso regular:** Los logs muestran accesos cada 5 minutos desde ambos orígenes:
   - `https://test-020-frontendbucket.s3.amazonaws.com` (legítimo)
   - `https://app-rewards-service.io` (sospechoso)

3. **Advertencias de deprecación:** Los logs muestran múltiples advertencias sobre Node.js v18.20.8, pero esto no está relacionado con el problema de seguridad.

4. **Ausencia de errores de autenticación:** No se observan fallos de autenticación, lo que sugiere que el atacante tiene acceso a tokens válidos.

## Relación con el código fuente

### Vulnerabilidad crítica identificada en `profile_service.js`:

```javascript
const responseHeaders = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": origin,  // ← VULNERABILIDAD CRÍTICA
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Session-Action"
};
```

**Problema:** El código establece dinámicamente el header `Access-Control-Allow-Origin` usando directamente el valor del header `origin` de la petición, sin validación alguna:

```javascript
const origin = event.headers.origin || event.headers.Origin || "*";
```

Esto permite que **cualquier dominio** pueda realizar peticiones CORS autenticadas a la API.

### Configuración permisiva en `template.yaml`:

```yaml
Cors:
  AllowMethods: "'GET,OPTIONS'"
  AllowHeaders: "'Content-Type,Authorization,X-Session-Action'"
  AllowOrigin: "'*'"  # ← Configuración demasiado permisiva
```

## Ejemplo de ejecución del ataque

**Escenario:** Un atacante desde `https://app-rewards-service.io` realiza una petición:

```javascript
// Petición maliciosa desde app-rewards-service.io
fetch('https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/user/profile', {
    method: 'GET',
    headers: {
        'Authorization': 'Bearer <JWT_REDACTADO>...',
        'Origin': 'https://app-rewards-service.io'
    },
    credentials: 'include'
});
```

**Respuesta del servidor:**
```javascript
{
    statusCode: 200,
    headers: {
        "Access-Control-Allow-Origin": "https://app-rewards-service.io", // ← Permite el acceso
        "Access-Control-Allow-Credentials": "true"
    },
    body: JSON.stringify({ 
        data: { userId: "user_123", session_active: true, /* datos sensibles */ },
        session_status: true 
    })
}
```

## Soluciones propuestas

### Solución 1: Lista blanca de dominios permitidos (Recomendada)

```javascript
// En profile_service.js
const ALLOWED_ORIGINS = [
    'https://test-020-frontendbucket.s3.amazonaws.com',
    'https://your-legitimate-domain.com',
    'http://localhost:3000' // Solo para desarrollo
];

const origin = event.headers.origin || event.headers.Origin;
const allowedOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : null;

const responseHeaders = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": allowedOrigin || "null",
    "Access-Control-Allow-Credentials": allowedOrigin ? "true" : "false",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Session-Action"
};

// Rechazar peticiones de orígenes no autorizados
if (!allowedOrigin && origin) {
    return {
        statusCode: 403,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ error: "Origin not allowed" })
    };
}
```

### Solución 2: Actualizar template.yaml

```yaml
Cors:
  AllowMethods: "'GET,OPTIONS'"
  AllowHeaders: "'Content-Type,Authorization,X-Session-Action'"
  AllowOrigin: "'https://test-020-frontendbucket.s3.amazonaws.com'"  # Dominio específico
```

### Solución 3: Implementar validación adicional de tokens

```javascript
// Agregar validación de referrer y user-agent
const referrer = event.headers.referer || event.headers.Referer;
const userAgent = event.headers['user-agent'] || event.headers['User-Agent'];

// Log de seguridad mejorado
console.log(JSON.stringify({
    level: "SECURITY",
    event: "AccessAttempt",
    requestId: event.requestContext.requestId,
    metadata: {
        origin: origin,
        referrer: referrer,
        userAgent: userAgent,
        sourceIP: event.requestContext.identity.sourceIp,
        allowed: ALLOWED_ORIGINS.includes(origin)
    }
}));
```

### Solución 4: Implementar rate limiting por origen

```javascript
// Implementar límites de peticiones por origen no autorizado
const RATE_LIMIT_SUSPICIOUS = 10; // peticiones por hora
// Usar DynamoDB para trackear peticiones por IP/origen
```

**Prioridad:** Esta vulnerabilidad debe ser corregida **inmediatamente** ya que permite el acceso no autorizado a información de sesiones desde cualquier dominio externo.