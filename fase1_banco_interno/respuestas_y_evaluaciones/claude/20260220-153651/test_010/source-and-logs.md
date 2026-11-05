Con toda la información recopilada, ya puedo construir el análisis completo.

---

## Truncamiento de nombres con tildes en perfiles de usuario

### Summary: El charset configurado en SES via SSM trunca los nombres al encontrar el primer carácter no-ASCII (tildes, acentos), mostrando "Jos" en lugar de "José" y "Mar" en lugar de "María".

### Severity: High

---

### Root Cause Analysis

**Pasos para reproducir**
1. Registrar usuario con nombre "José" o "María" desde el formulario.
2. El registro se almacena correctamente en DynamoDB (sin problemas de encoding).
3. El stream de DynamoDB dispara `SendEmailServiceFunction`.
4. La lambda `email.ts` construye el cuerpo del email e invoca SES con el charset definido en `EMAIL_CHARSET`.
5. El email (y/o la respuesta de perfil) muestra "Jos" o "Mar".

**Expected vs. Actual**
- Esperado: nombre completo "José García"
- Actual: "Jos García" (truncado en el primer carácter multibyte)

**Location del bug**

`src/handlers/email.ts` — líneas **50** y **55**:

```typescript
Subject: {
  Data: "Welcome to our Service",
  Charset: EMAIL_CHARSET,    // <-- línea 50
},
Body: {
  Text: {
    Data: templateContent,
    Charset: EMAIL_CHARSET,  // <-- línea 55
  },
},
```

`EMAIL_CHARSET` se resuelve desde SSM en `template.yaml` línea **111**:
```yaml
EMAIL_CHARSET: '{{resolve:ssm:/bw-010/email/charset}}'
```

**Mecanismo del error**

El parámetro SSM `/bw-010/email/charset` tiene el valor `ASCII` en lugar de `UTF-8`. SES, al intentar codificar el cuerpo del email con charset ASCII, encuentra que `é` (U+00E9, 2 bytes en UTF-8: `0xC3 0xA9`) supera el rango ASCII (0-127) y trunca la cadena en ese punto:

```
"José"  → J(ASCII ok) + o(ASCII ok) + s(ASCII ok) + é(no-ASCII → STOP) → "Jos"
"María" → M(ASCII ok) + a(ASCII ok) + r(ASCII ok) + í(no-ASCII → STOP) → "Mar"
```

Los logs de CloudWatch no muestran errores de aplicación porque SES no lanza excepción al truncar — simplemente entrega el contenido con el charset configurado. El almacenamiento en DynamoDB es correcto (DynamoDB usa UTF-8 nativo), pero la información del perfil que el usuario recibe por email queda truncada.

---

### Solution

**Acción inmediata**: actualizar el parámetro SSM en AWS:

```bash
aws ssm put-parameter \
  --name "/bw-010/email/charset" \
  --value "UTF-8" \
  --type String \
  --overwrite
```

**Defensa en profundidad en `src/handlers/email.ts`**: dado que el valor proviene de configuración externa, agregar una validación o un valor por defecto seguro:

```typescript
const EMAIL_CHARSET = process.env.EMAIL_CHARSET ?? "UTF-8";
```

Esto evita que un valor de SSM incorrecto vuelva a producir el mismo problema silenciosamente. El parámetro correcto debe ser `UTF-8` para soportar caracteres de todos los idiomas (español, portugués, francés, etc.).

# Total cost USD

0.5451967500000001

# Execution time in seconds: 

111
