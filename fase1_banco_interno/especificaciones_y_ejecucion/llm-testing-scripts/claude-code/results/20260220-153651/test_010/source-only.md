Analizo todos los archivos del proyecto en paralelo ya los tengo. Procedo con el análisis.

---

## Error en registro de usuarios: ConditionExpression comentado y acceso inseguro a atributos DynamoDB

### Summary: La proteccion contra duplicados en el registro esta deshabilitada y el handler de email accede a atributos sin validacion previa, ambos generando comportamiento incorrecto en produccion.

### Severity: High

---

### Root Cause Analysis

Se identificaron **dos bugs** en el codigo fuente:

---

#### Bug 1 — `register.ts:47` — ConditionExpression comentado (logica muerta)

**Ubicacion:** `src/handlers/register.ts:47` y `src/handlers/register.ts:59`

```typescript
// register.ts:38-48
const command = new PutCommand({
  TableName: "Users",
  Item: { email, first_name, last_name, birth_date, genre },
  // ConditionExpression: "attribute_not_exists(email)" // <-- COMENTADO
});
```

**Problema:**
- La `ConditionExpression` que impide sobrescribir usuarios con el mismo email esta comentada.
- Esto convierte el `PutCommand` en un **upsert silencioso**: si un email ya existe, el registro se sobreescribe sin ningun error.
- Como consecuencia directa, el bloque `catch` en `register.ts:59` que maneja `ConditionalCheckFailedException` es **codigo muerto** — esa excepcion jamas sera lanzada y el `statusCode: 409` nunca sera retornado al cliente.

**Flujo esperado vs real:**

| Caso | Esperado | Real |
|------|----------|------|
| Email ya registrado | HTTP 409, registro no modificado | HTTP 201, registro sobreescrito silenciosamente |

---

#### Bug 2 — `email.ts:21-26` — Acceso a `.S` sin validacion previa del atributo padre

**Ubicacion:** `src/handlers/email.ts:21-26`

```typescript
// email.ts:21-26
const email = newImage.email.S;         // TypeError si newImage.email es undefined
const firstName = newImage.first_name.S; // TypeError si newImage.first_name es undefined
const lastName = newImage.last_name.S;   // TypeError si newImage.last_name es undefined
const birthDate = newImage.birth_date.S; // TypeError si newImage.birth_date es undefined

if (!email || !firstName) {  // <-- validacion llega tarde y es incompleta
```

**Problema:**
- El acceso a `.S` en cada atributo ocurre **antes** de cualquier validacion de existencia.
- Si alguno de los atributos (`last_name`, `birth_date`) no existe en el `NewImage` del stream, se lanza un `TypeError: Cannot read properties of undefined (reading 'S')`.
- Este error ocurre **fuera del bloque `try/catch`** de la linea 41, por lo tanto **no es capturado**. El Lambda falla con una excepcion no controlada.
- La validacion en linea 26 solo cubre `email` y `firstName`, ignorando `lastName` y `birthDate`, y ademas llega despues del acceso inseguro.
- Un fallo no capturado en un DynamoDB Stream trigger puede generar un **ciclo de reintentos infinitos** si el registro problematico permanece en el stream.

---

### Solution

**Para Bug 1 — `register.ts:47`:**

Descomentar el `ConditionExpression` para activar la proteccion contra duplicados:

```typescript
const command = new PutCommand({
  TableName: "Users",
  Item: { email, first_name, last_name, birth_date, genre },
  ConditionExpression: "attribute_not_exists(email)",
});
```

Esto permite que el `ConditionalCheckFailedException` sea lanzado correctamente y el handler retorne HTTP 409 como estaba disenado.

---

**Para Bug 2 — `email.ts:21-26`:**

Validar la existencia de cada atributo en `newImage` antes de acceder a `.S`, y hacerlo dentro del bloque protegido:

```typescript
const email = newImage.email?.S;
const firstName = newImage.first_name?.S;
const lastName = newImage.last_name?.S;
const birthDate = newImage.birth_date?.S;

if (!email || !firstName || !lastName || !birthDate) {
  console.warn("Skipping record with missing required fields");
  continue;
}
```

El uso del operador optional chaining (`?.`) evita el `TypeError` cuando el atributo padre es `undefined`, y la validacion extendida asegura que todos los campos necesarios para construir el email esten presentes antes de intentar el envio.

# Total cost USD

0.25596399999999997

# Execution time in seconds: 

86
