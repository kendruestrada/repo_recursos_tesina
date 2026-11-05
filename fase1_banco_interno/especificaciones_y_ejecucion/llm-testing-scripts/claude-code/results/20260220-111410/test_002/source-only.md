---

## Inconsistencia Reproducible en Flujo de Pago: Respuesta del Servicio Externo Ignorada

### Summary: La variable `response` del servicio de pago externo se obtiene pero nunca se lee, haciendo que el pago siempre se guarde como exitoso independientemente del resultado real.

### Severity: Critical

---

### Root Cause Analysis

**Bugs identificados en orden de severidad:**

---

**Bug 1 — CRITICO: Respuesta del servicio externo completamente ignorada**
`src/internal_services/SavePayment.js:28-43`

```js
const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId), {
    method: "GET",
    ...
});
// `response` nunca se lee: ni response.ok, ni response.status, ni response.json()

await docClient.send(new PutCommand({
    Item: {
        payment_status: "success",   // hardcodeado
        order_status: "paid",        // hardcodeado
        ...
    }
}));
```

La variable `response` se asigna en la línea 28 y **nunca se vuelve a usar**. El flujo continua incondicionalmente guardando el pago como `"success"` / `"paid"` en DynamoDB. Esto es la causa raiz de la inconsistencia: sin importar si el servicio externo retorna `200`, `404`, `500`, o incluso falla completamente, el estado local siempre queda como pagado.

- **Esperado:** verificar `response.ok` o `response.status` antes de persistir el estado
- **Actual:** el resultado del servicio externo se descarta, el pago se guarda como exitoso siempre

---

**Bug 2 — CRITICO: Conflicto de tipo de modulo en `package.json`**
`package.json:4` vs `SavePayment.js:1-2,10`

```json
"type": "module"
```

```js
const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");  // CommonJS
exports.handler = async (event) => { ... }                         // CommonJS
```

El `package.json` declara `"type": "module"` (ES Modules), pero el codigo usa `require()` y `exports.handler` que son sintaxis CommonJS. Node.js 18 lanzará el error `require is not defined in ES module scope` al intentar cargar el modulo. La Lambda fallara en el inicio, sin ejecutar ninguna linea.

- **Esperado:** consistencia entre tipo de modulo declarado y sintaxis usada
- **Actual:** la funcion Lambda no puede iniciar

---

**Bug 3 — ALTO: Respuesta de confirmacion no validada**
`src/internal_services/SavePayment.js:49-58`

```js
const confirmationResponse = await fetch(externalPaymentServiceConfirmationUrl...);
console.info("CONFIRMATION_RESPONSE", {
    status: confirmationResponse.status,   // solo se loguea
    statusText: confirmationResponse.statusText
});
// nunca se verifica si fue exitosa
return { statusCode: 200, ... };  // siempre retorna 200
```

El estado de la confirmacion al servicio externo se loguea pero nunca se evalua. Un `4xx` o `5xx` del servicio de confirmacion pasa silenciosamente y la funcion retorna `200` al cliente.

---

### Steps to reproduce

1. Invocar `GET /payment-callback?transaction_id=TXN-001`
2. El servicio externo retorna cualquier respuesta (exitosa o fallida)
3. DynamoDB registra `payment_status: "success"` y `order_status: "paid"`
4. No hay correlacion entre el estado real del pago y lo persistido localmente

---

### Solution

**Bug 1 — leer y validar la respuesta antes de persistir:**
```js
const response = await fetch(...);
if (!response.ok) {
    return { statusCode: 400, body: JSON.stringify({ error: "payment_not_confirmed" }) };
}
const paymentData = await response.json();
// usar paymentData.status para determinar payment_status y order_status
```

**Bug 2 — eliminar `"type": "module"` del `package.json`** o migrar el codigo a ESM (`import`/`export`).

**Bug 3 — validar `confirmationResponse.ok`** antes de retornar `200`.

# Total cost USD

0.29980505

# Execution time in seconds: 

96
