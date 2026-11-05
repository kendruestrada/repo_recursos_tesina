## Análisis del Ticket de Soporte Técnico

**Ticket:** Los usuarios con nombres que contienen tildes (José, María) aparecen truncados en sus perfiles, mostrando solo 'Jos', 'Mar' en lugar del nombre completo.

## Hallazgos en los logs

Analizando los logs de CloudWatch, se observa un patrón consistente en el servicio de email donde aparece:

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

**Problema identificado:** El charset configurado es `ISO-8859-1` (Latin-1), que tiene limitaciones para caracteres con tildes y otros caracteres especiales del español.

## Relación con el código fuente

### 1. Configuración del Charset en `template.yaml`
```yaml
EmailServiceFunction:
  Environment:
    Variables:
      EMAIL_CHARSET: '{{resolve:ssm:/bw-010/email/charset}}'
```

### 2. Uso del charset en `src/handlers/email.ts`
```typescript
const EMAIL_CHARSET = process.env.EMAIL_CHARSET;

// Usado en:
Message: {
  Subject: {
    Data: "Welcome to our Service",
    Charset: EMAIL_CHARSET,  // ISO-8859-1
  },
  Body: {
    Text: {
      Data: templateContent,
      Charset: EMAIL_CHARSET,  // ISO-8859-1
    },
  },
}
```

### 3. Almacenamiento en DynamoDB
El problema no está en el almacenamiento (DynamoDB maneja UTF-8 nativamente), sino en la codificación utilizada para el envío de emails y posiblemente en la visualización.

## Ejemplo de ejecución

**Entrada esperada:**
- Nombre: "José García"
- Email: "jose@example.com"

**Flujo actual:**
1. DynamoDB almacena correctamente: `first_name: "José García"`
2. Email service lee: `firstName = "José García"`
3. SES envía con charset ISO-8859-1: caracteres con tilde se corrompen o truncan
4. El usuario recibe: "Hello Jos García" (truncado)

**Comportamiento esperado:**
- Email debería mostrar: "Hello José García" (completo)

## Solución propuesta

### Solución Principal: Cambiar charset a UTF-8

1. **Actualizar el parámetro SSM:**
```bash
aws ssm put-parameter \
  --name "/bw-010/email/charset" \
  --value "UTF-8" \
  --type "String" \
  --overwrite
```

2. **Verificar compatibilidad en el código:**
El código actual en `email.ts` ya está preparado para usar cualquier charset desde la variable de entorno, por lo que no requiere cambios.

### Solución Alternativa: Hardcodear UTF-8

Si no se puede modificar el parámetro SSM, modificar `src/handlers/email.ts`:

```typescript
// Cambiar esta línea:
const EMAIL_CHARSET = process.env.EMAIL_CHARSET;

// Por esta:
const EMAIL_CHARSET = process.env.EMAIL_CHARSET || "UTF-8";
```

### Solución de Respaldo: Validación de entrada

Agregar validación en `src/handlers/register.ts` para detectar caracteres especiales:

```typescript
// Función auxiliar para validar caracteres
const hasSpecialChars = (text: string): boolean => {
  return /[àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]/i.test(text);
};

// En el handler de registro:
if (hasSpecialChars(first_name) || hasSpecialChars(last_name)) {
  console.warn(`Special characters detected in name: ${first_name} ${last_name}`);
}
```

## Recomendación

**Implementar la Solución Principal** cambiando el charset a UTF-8, ya que:
- Es la codificación estándar para aplicaciones web modernas
- Soporta todos los caracteres del español y otros idiomas
- No requiere cambios en el código fuente
- Es compatible con SES y DynamoDB

Después del cambio, realizar pruebas con nombres que contengan tildes para verificar que se muestran correctamente tanto en los emails como en las consultas de usuarios.