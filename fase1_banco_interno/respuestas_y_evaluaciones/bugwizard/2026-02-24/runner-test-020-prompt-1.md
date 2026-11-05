## Análisis del Ticket de Seguridad

**Ticket:** El equipo de ciberseguridad reporta que la información de sesión puede ser obtenida desde sitios externos sospechosos, comprometiendo la validación de sesiones activas en la base de datos.

## Hallazgos en los logs:

Analizando los logs de CloudWatch, se identifican múltiples patrones preocupantes:

1. **Orígenes sospechosos accediendo al endpoint:**
   - `https://app-rewards-service.io` - Dominio externo no autorizado
   - `https://test-020-frontendbucket.s3.amazonaws.com` - Bucket S3 legítimo

2. **Patrón de acceso sistemático:** Los logs muestran accesos cada 5 minutos desde ambos orígenes, sugiriendo automatización o scraping.

3. **Ausencia de errores de autenticación:** Todos los requests retornan código 200, indicando que el sistema está permitiendo acceso desde orígenes no autorizados.

## Relación con el código fuente:

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

**Problema:** El código está configurando dinámicamente el header `Access-Control-Allow-Origin` con cualquier origen que llegue en la request, sin validación alguna.

### Configuración permisiva en `template.yaml`:
```yaml
Cors:
  AllowOrigin: "'*'"  # ← Configuración demasiado permisiva
```

## Ejemplo de ejecución:

**Escenario de ataque:**
1. Atacante desde `https://app-rewards-service.io` envía request:
   ```
   GET /user/profile
   Origin: https://app-rewards-service.io
   Authorization: Bearer <JWT_REDACTADO>...
   ```

2. El código ejecuta:
   ```javascript
   const origin = "https://app-rewards-service.io"; // Sin validación
   // ... procesamiento ...
   return {
       statusCode: 200,
       headers: {
           "Access-Control-Allow-Origin": "https://app-rewards-service.io", // Permite el origen malicioso
           "Access-Control-Allow-Credentials": "true" // ¡Permite envío de cookies/tokens!
       }
   };
   ```

3. **Resultado:** El navegador permite que el sitio malicioso acceda a la respuesta con credenciales.

## Soluciones propuestas:

### Solución 1: Lista blanca de orígenes (Recomendada)
```javascript
const ALLOWED_ORIGINS = [
    'https://test-020-frontendbucket.s3.amazonaws.com',
    'https://your-company-domain.com',
    'http://localhost:3000' // Solo para desarrollo
];

const origin = event.headers.origin || event.headers.Origin;
const allowedOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];

const responseHeaders = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Session-Action"
};
```

### Solución 2: Validación adicional de tokens
```javascript
// Agregar validación de issuer en el JWT
if (authHeader && authHeader.startsWith("Bearer ")) {
    try {
        const token = authHeader.split(" ")[1];
        const payload = JSON.parse(Buffer.from(token.split(".")[1], "base64").toString());
        
        // Validar issuer y audience
        if (payload.iss !== 'your-trusted-issuer' || !payload.aud.includes('your-app')) {
            throw new Error('Invalid token issuer or audience');
        }
        
        userId = payload.sub;
    } catch (e) {
        return {
            statusCode: 401,
            headers: { "Access-Control-Allow-Origin": allowedOrigin },
            body: JSON.stringify({ error: "Unauthorized" })
        };
    }
}
```

### Solución 3: Actualizar template.yaml
```yaml
Cors:
  AllowMethods: "'GET,OPTIONS'"
  AllowHeaders: "'Content-Type,Authorization,X-Session-Action'"
  AllowOrigin: "'https://test-020-frontendbucket.s3.amazonaws.com'" # Origen específico
```

### Solución 4: Implementar rate limiting
```javascript
// Agregar validación de rate limiting por IP/origen
const rateLimitKey = `${origin}:${event.requestContext.identity.sourceIp}`;
// Implementar lógica de rate limiting usando DynamoDB o ElastiCache
```

**Prioridad:** Esta es una vulnerabilidad de seguridad crítica que debe ser corregida inmediatamente, ya que permite a sitios maliciosos acceder a información de sesión de usuarios autenticados.