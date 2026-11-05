Tengo toda la información necesaria. Los logs de `SendEmailServiceFunction` revelan la evidencia clave.

---

## Corrupcion de caracteres con tilde en nombres de usuario

### Summary: El charset `ISO-8859-1` configurado para el servicio de email causa que los caracteres UTF-8 de tildes se interpreten incorrectamente, truncando o corrompiendo nombres como "José" y "María" al recibirlos en el correo de bienvenida.

### Severity: High

---

### Root Cause Analysis

**Evidencia directa en los logs** (`/aws/lambda/SendEmailServiceFunction`):

El log de `DispatchingEmailToSES` revela el payload enviado a SES:
```json
"Subject": { "Data": "Welcome to our Service", "Charset": "ISO-8859-1" },
"Body":    { "Text": { "Data": "Hello José García,...", "Charset": "ISO-8859-1" }}
```

El charset es `ISO-8859-1`, resuelto desde el parametro SSM `/bw-010/email/charset`.

**Flujo de ejecucion y punto de falla:**

1. El usuario registra su nombre "José" → `register.ts` lo almacena en DynamoDB correctamente como string Unicode (UTF-8)
2. El stream de DynamoDB dispara `email.ts` (`src/handlers/email.ts:19-24`) que lee `first_name` y `last_name` del `NewImage`
3. Se construye el `SendEmailCommand` (`email.ts:42-59`) con:
   - `Data: templateContent` — string de Node.js en memoria, codificado en UTF-8
   - `Charset: EMAIL_CHARSET` — resuelto como `"ISO-8859-1"` desde SSM (`template.yaml:111`)
4. El SDK de AWS envía el payload en UTF-8 a la API de SES; SES construye el mensaje MIME declarando `Content-Type: text/plain; charset=ISO-8859-1`
5. El cliente de correo del usuario recibe bytes UTF-8 pero los interpreta como ISO-8859-1:

| Caracter | Bytes UTF-8 | Interpretacion ISO-8859-1 |
|---|---|---|
| `é` (José) | `0xC3 0xA9` | `Ã` + `©` |
| `í` (María) | `0xC3 0xAD` | `Ã` + soft-hyphen `­` (invisible) |

Para "María": `0xAD` es el **soft hyphen** (guion suave, U+00AD), un caracter de control invisible que muchos clientes de correo interpretan como fin de segmento o ignoracion de lo que precede, produciendo "Mar" en lugar de "María". Para "José", `©` provoca sustituciones visuales o truncamientos segun el cliente.

**Ubicacion del bug:**

- `template.yaml:111` — parametro SSM que resuelve a `ISO-8859-1`:
  ```yaml
  EMAIL_CHARSET: '{{resolve:ssm:/bw-010/email/charset}}'
  ```
- `src/handlers/email.ts:48,54` — uso del charset en el comando SES:
  ```typescript
  Subject: { Data: "...", Charset: EMAIL_CHARSET },
  Body: { Text: { Data: templateContent, Charset: EMAIL_CHARSET } }
  ```

**Expected vs. Actual:**
- **Esperado:** El usuario recibe "Hello José García" con tildes correctas
- **Actual:** El usuario recibe "Hello JosÃ© GarcÃ­a" o truncamientos como "Jos"/"Mar" dependiendo del cliente de correo

**Nota:** El frontend (`index.html:5`) tiene `<meta charset="UTF-8">` y la funcion `search.ts` retorna JSON correcto desde DynamoDB — el problema es exclusivamente en el envio del email.

---

### Solution

**Cambio requerido:** Actualizar el parametro SSM `/bw-010/email/charset` de `ISO-8859-1` a `UTF-8`.

```bash
aws ssm put-parameter \
  --name "/bw-010/email/charset" \
  --value "UTF-8" \
  --type String \
  --overwrite
```

Alternativamente, si se prefiere no depender del SSM para este valor, hardcodear directamente en `template.yaml:111`:

```yaml
EMAIL_CHARSET: 'UTF-8'
```

Esto garantiza que la declaracion del charset en el header MIME coincida con la codificacion real de los bytes enviados por el SDK (UTF-8), permitiendo que todos los caracteres Unicode — incluyendo tildes, enyes y otros — sean renderizados correctamente en cualquier cliente de correo.

# Total cost USD

0.6735815

# Execution time in seconds: 

173
