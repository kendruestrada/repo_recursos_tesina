## Análisis del Ticket de Soporte

**Ticket:** Usuarios con nombres que contienen tildes (José, María) aparecen truncados como 'Jos', 'Mar' en sus perfiles y correos de bienvenida.

## Hallazgos en los logs

Analizando los logs de CloudWatch, se observa un patrón consistente en todos los correos enviados:

```json
{
  "event": "DispatchingEmailToSES",
  "recipient": "preslee.jeancarlo@dropmeon.com",
  "ses_payload": {
    "Source": "usuario@example.com",
    "Destination": {"ToAddresses": ["preslee.jeancarlo@dropmeon.com"]},
    "Message": {
      "Subject": {"Data": "Welcome to our Service", "Charset": "ISO-8859-1"},
      "Body": {
        "Text": {
          "Data": "\n        Hello José García,\n        \n        Welcome! We have registered your details:\n        Birth Date: 1990-01-01\n        \n        Best regards,\n        The Team\n      ",
          "Charset": "ISO-8859-1"
        }
      }
    }
  }
}
```

**Problema identificado:** El charset configurado es `ISO-8859-1` (Latin-1), que tiene limitaciones para caracteres especiales y puede causar truncamiento o corrupción de caracteres con tildes.

## Relación con el código fuente

### 1. Configuración del Charset en `template.yaml`
```yaml
Environment:
  Variables:
    SOURCE_EMAIL: '{{resolve:ssm:/bw-010/email/source}}'
    EMAIL_CHARSET: '{{resolve:ssm:/bw-010/email/charset}}'
```

### 2. Uso del Charset en `email.ts`
```typescript
Message: {
  Subject: {
    Data: "Welcome to our Service",
    Charset: EMAIL_CHARSET,  // Usando ISO-8859-1
  },
  Body: {
    Text: {
      Data: templateContent,
      Charset: EMAIL_CHARSET,  // Usando ISO-8859-1
    },
  },
}
```

### 3. Construcción del mensaje
```typescript
const templateContent = `
  Hello ${firstName} ${lastName},
  
  Welcome! We have registered your details:
  Birth Date: ${birthDate}
  
  Best regards,
  The Team
`;
```

## Ejemplo de ejecución

**Entrada esperada:**
- firstName: "José"
- lastName: "García"

**Procesamiento actual:**
1. DynamoDB almacena correctamente: `José García`
2. El servicio de email construye: `Hello José García,`
3. SES procesa con charset `ISO-8859-1`
4. **Resultado:** Los caracteres `é` se truncan o corrompen

**Comportamiento esperado con UTF-8:**
1. DynamoDB almacena: `José García`
2. Email construye: `Hello José García,`
3. SES procesa con charset `UTF-8`
4. **Resultado:** `Hello José García,` (correcto)

## Soluciones propuestas

### Solución Principal: Cambiar charset a UTF-8

**1. Actualizar el parámetro SSM:**
```bash
aws ssm put-parameter \
  --name "/bw-010/email/charset" \
  --value "UTF-8" \
  --type "String" \
  --overwrite
```

**2. Verificar la codificación en el código (opcional pero recomendado):**
```typescript
// En email.ts, agregar validación explícita
const EMAIL_CHARSET = process.env.EMAIL_CHARSET || 'UTF-8';

// Asegurar que el contenido esté correctamente codificado
const templateContent = `
  Hello ${firstName} ${lastName},
  
  Welcome! We have registered your details:
  Birth Date: ${birthDate}
  
  Best regards,
  The Team
`;
```

### Solución Alternativa: Validación de entrada

**3. Agregar validación en `register.ts`:**
```typescript
// Validar que los caracteres especiales se manejen correctamente
const validateUTF8 = (text: string): boolean => {
  try {
    return Buffer.from(text, 'utf8').toString('utf8') === text;
  } catch {
    return false;
  }
};

// En el handler de registro
if (!validateUTF8(first_name) || !validateUTF8(last_name)) {
  return {
    statusCode: 400,
    body: JSON.stringify({ 
      message: "Invalid characters in name fields" 
    }),
  };
}
```

### Solución de Respaldo: Escape de caracteres

**4. Si no se puede cambiar el charset, escapar caracteres:**
```typescript
const escapeForISO88591 = (text: string): string => {
  return text
    .replace(/á/g, 'a').replace(/Á/g, 'A')
    .replace(/é/g, 'e').replace(/É/g, 'E')
    .replace(/í/g, 'i').replace(/Í/g, 'I')
    .replace(/ó/g, 'o').replace(/Ó/g, 'O')
    .replace(/ú/g, 'u').replace(/Ú/g, 'U')
    .replace(/ñ/g, 'n').replace(/Ñ/g, 'N');
};
```

## Recomendación

**La solución más efectiva es cambiar el charset a UTF-8**, ya que:
1. Es el estándar moderno para manejo de caracteres internacionales
2. Soporta todos los caracteres especiales sin pérdida de información
3. Es compatible con SES de Amazon
4. Requiere cambios mínimos en el código existente

Después del cambio, redesplegar la aplicación con `sam deploy` para que tome el nuevo valor del parámetro SSM.