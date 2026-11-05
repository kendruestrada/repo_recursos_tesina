Con los logs y el codigo fuente analizados, puedo identificar claramente la causa raiz.

---

## [Bug]: Pago persistido como exitoso sin verificar respuesta del servicio externo

### Summary: El handler guarda el pago con `payment_status: "success"` de forma incondicional, ignorando por completo la respuesta del servicio externo de verificacion.

### Severity: Critical

---

### Root Cause Analysis

**Flujo esperado:**
1. Usuario completa la compra en plataforma externa.
2. Plataforma externa redirige al callback de nuestro sistema.
3. Nuestro sistema consulta al servicio externo para verificar el estado del pago.
4. Solo si el pago fue exitoso, se persiste como `payment_status: "success"`.
5. Se notifica a la plataforma externa que el pago fue guardado.

**Flujo actual (con el bug):**

En `src/internal_services/SavePayment.js`, lineas 26-44:

```javascript
// Linea 26: se realiza la consulta al servicio externo...
const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId), {
    method: "GET",
    headers: { "Content-Type": "application/json" }
});

// Linea 33: ...pero 'response' NUNCA se lee ni se valida.
// Se guarda inmediatamente como "success" sin importar el resultado:
await docClient.send(new PutCommand({
    TableName: tableName,
    Item: {
        transaction_id: transactionId,
        payment_status: "success",   // <-- hardcodeado, siempre "success"
        order_status: "paid",
        processed_at: new Date().toISOString()
    }
}));
```

**Evidencia en logs** (`/aws/lambda/bw-002-SavePayment`):

El patron se repite en el 100% de las invocaciones:
```
PAYMENT_CALLBACK_RECEIVED   { transaction_id: 'TRX_CANARY_xxx' }
LOCAL_PAYMENT_PERSISTED     { transaction_id: 'TRX_CANARY_xxx' }   <-- guardado sin validar
CONFIRMATION_RESPONSE       { status: 404, statusText: 'Not Found' } <-- falla ignorada
```

Dos problemas encadenados:
- **Problema 1:** La respuesta del `GET` al servicio externo (verificacion del pago) se asigna a `response` pero nunca se evalua. El sistema no sabe si el pago fue aprobado o rechazado.
- **Problema 2:** `CONFIRMATION_RESPONSE` devuelve `404` en todas las invocaciones sin excepcion, lo que indica que la URL de confirmacion es incorrecta o el endpoint no existe. Este error se logea pero no lanza excepcion ni altera el flujo.

**Ubicacion del bug:**
- Archivo: `src/internal_services/SavePayment.js`
- Lineas criticas: 26-44 (ignorar `response`) y 36 (`payment_status: "success"` hardcodeado)

---

### Solution

1. **Leer y validar la respuesta del servicio externo** antes de persistir el pago. Si el estado no es exitoso, retornar error y no guardar en DynamoDB.

2. **Derivar el `payment_status` desde la respuesta real** del servicio externo en lugar de hardcodearlo.

3. **Manejar el error 404 del endpoint de confirmacion:** evaluar `confirmationResponse.ok` y lanzar error o registrar adecuadamente para no silenciar una falla en la notificacion a la plataforma externa.

```javascript
const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId), {
    method: "GET",
    headers: { "Content-Type": "application/json" }
});

// Validar respuesta antes de persistir
if (!response.ok) {
    console.error("EXTERNAL_PAYMENT_VERIFICATION_FAILED", {
        transaction_id: transactionId,
        status: response.status
    });
    return { statusCode: 402, body: JSON.stringify({ error: "Payment not confirmed by external service" }) };
}

const paymentData = await response.json();

// Usar el estado real del servicio externo
await docClient.send(new PutCommand({
    TableName: tableName,
    Item: {
        transaction_id: transactionId,
        payment_status: paymentData.status,   // estado real, no hardcodeado
        order_status: paymentData.status === "approved" ? "paid" : "pending",
        processed_at: new Date().toISOString()
    }
}));
```

# Total cost USD

0.46881985

# Execution time in seconds: 

111
