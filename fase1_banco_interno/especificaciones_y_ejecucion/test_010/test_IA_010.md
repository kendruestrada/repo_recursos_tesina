# Resumen de hallazgos

## Hallazgos

- **URL del API en el frontend (posible `users`)**: el output `WebEndpoint` en `template.yaml:170-173` termina con `/` y el frontend concatena `${API_URL}/users` en `index.html:104-132`. Esto puede generar rutas con doble `/` y provocar `404` o comportamiento raro según el gateway.

- **Lambda de email frágil si faltan variables de entorno**: en `email.ts:8-13` hace `throw` si no existen `SOURCE_EMAIL` o `EMAIL_CHARSET`, lo que puede tumbar la Lambda en frío si el entorno/SSM no está bien.

- **Envío de email también en `MODIFY`**: el stream filtra `INSERT` y `MODIFY` en `template.yaml:103-110` y el handler procesa ambos en `email.ts:12-18`. Con `Put` sin condición, re-registros pueden disparar correos repetidos.

- **Búsqueda/listado limitado y caro**: el listado usa `Scan` con `Limit: 20` en `search.ts:33-49`. Puede parecer “faltan usuarios” y `Scan` escala mal.

## Problemas típicos de consistencia/normalización (muy comunes en prod)

- `GetItem` por email exige coincidencia exacta (mayúsculas/espacios fallan).
- Lecturas inmediatas tras escribir pueden fallar si no son consistentes.

## Cambios defensivos aplicados (para evitar errores intermitentes)

- Parsing robusto del body (incluye `base64`) y normalización de email en `register.ts`.
- Normalización de email + `ConsistentRead: true` en el `Get` de `search.ts`.
- `USERS_TABLE_NAME` por variable de entorno en `template.yaml` para evitar desajustes de nombre de tabla entre entornos.