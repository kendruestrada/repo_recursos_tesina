Con el análisis completo del codigo fuente y los logs, aqui está el diagnostico:

---

## Pagos marcados como exitosos sin debito real

### Summary: El sistema guarda todos los pagos como "exitosos" sin verificar la respuesta del servicio externo, y la notificacion de confirmacion falla sistematicamente con HTTP 404.

### Severity: Critical

---

### Root Cause Analysis

**Dos problemas independientes, ambos en `src/internal_services/SavePayment.js`:**

---

#### Problema 1 (Critico) — Respuesta de verificacion nunca es evaluada

**Ubicacion:** `SavePayment.js:28-43`

El handler llama al servicio externo para obtener el estado del pago:

```js
// linea 28
const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId), {
    method: "GET",
    ...
});

// linea 35 — inmediatamente despues, sin leer ni validar `response`
await docClient.send(new PutCommand({
    ...
    Item: {
        payment_status: "success",   // hardcodeado siempre como exitoso
        ...
    }
}));
```

La variable `response` es recibida pero **nunca se lee su body ni se valida su `status`**. Sin importar lo que responda la plataforma externa (pago pendiente, rechazado, fallido), el sistema escribe `payment_status: "success"` de forma incondicional.

**Flujo real vs esperado:**

| Paso | Esperado | Real |
|---|---|---|
| Fetch externo | Obtener estado real del pago | Se hace el fetch pero se ignora |
| Guardado en BD | Solo guardar si pago aprobado | Siempre guarda como `"success"` |

**Ejemplo de ejecucion hipotetica:**
- `transaction_id = TRX_CANARY_a4f074`
- Plataforma externa responde `{ status: "rejected" }`
- `response.status` nunca se lee
- DynamoDB recibe: `{ payment_status: "success", order_status: "paid" }`
- Usuario ve pago exitoso, pero no hubo debito

---

#### Problema 2 (Alto) — Confirmacion a plataforma externa falla con 404 en el 100% de los casos

**Evidencia en logs (patron consistente, ultimas 72 horas):**

```
CONFIRMATION_RESPONSE { status: 404, statusText: 'Not Found' }
```

Este error aparece en **absolutamente todas** las invocaciones registradas. La URL configurada en `EXTERNAL_PAYMENT_SERVICE_CONFIRMATION_URL` apunta a un endpoint inexistente o esta mal configurada. Ademas, el codigo no trata este 404 como error — solo lo loguea y retorna `statusCode: 200` de todas formas.

**Ubicacion:** `SavePayment.js:49-58`

```js
const confirmationResponse = await fetch(externalPaymentServiceConfirmationUrl...);
console.info("CONFIRMATION_RESPONSE", {
    status: confirmationResponse.status,  // 404 siempre
    ...
});
// no hay validacion, no hay throw, retorna 200 igual
```

Esto significa que la plataforma externa **nunca recibe la confirmacion de guardado**. El flujo descrito por el negocio ("una vez guardado en nuestros sistemas le informamos a la plataforma externa") esta roto en su totalidad.

---

#### Error adicional (Medio) — Fallo de red en fetch inicial

**Log del 2026-02-17:**
```
TypeError: fetch failed
  at SavePayment.js:28:22
  SocketError: other side closed (UND_ERR_SOCKET)
```

El fetch a `EXTERNAL_PAYMENT_SERVICE_URL` fallo por cierre de socket. No hay manejo de errores (`try/catch`) en el handler, por lo que este tipo de fallo propaga una excepcion no controlada que aborta la ejecucion.

---

### Solution

**Fix 1 — Leer y validar la respuesta del servicio externo antes de guardar:**

```js
const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId), {
    method: "GET",
    headers: { "Content-Type": "application/json" }
});

const paymentData = await response.json();

// Validar que el pago fue realmente aprobado
if (!response.ok || paymentData.status !== "approved") {
    console.error("PAYMENT_NOT_APPROVED", { transaction_id: transactionId, paymentData });
    return {
        statusCode: 422,
        body: JSON.stringify({ error: "Payment not approved by external service" })
    };
}

// Solo entonces guardar en DynamoDB
await docClient.send(new PutCommand({ ... }));
```

**Fix 2 — Tratar el 404 de confirmacion como error y corregir la URL:**

Verificar el valor de la variable de entorno `EXTERNAL_PAYMENT_SERVICE_CONFIRMATION_URL` en la configuracion del Lambda (o en `template.yaml`). La URL actual no resuelve a ningun endpoint valido. Ademas, agregar validacion:

```js
if (!confirmationResponse.ok) {
    console.error("CONFIRMATION_FAILED", { status: confirmationResponse.status });
    // Decidir si reintentar o lanzar error segun el contrato con la plataforma
}
```

**Fix 3 — Envolver el handler en try/catch:**

```js
exports.handler = async (event) => {
    try {
        // ... logica actual
    } catch (error) {
        console.error("HANDLER_ERROR", { message: error.message, stack: error.stack });
        return { statusCode: 500, body: JSON.stringify({ error: "Internal error" }) };
    }
};
```

# Total cost USD

0.4018535

# Execution time in seconds: 

88
