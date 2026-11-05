## Pagos Marcados como Exitosos Sin Debito Real: Respuesta Ignorada del Servicio Externo

### Summary: El sistema guarda el pago con estado `"success"` hardcodeado sin validar la respuesta del servicio externo de verificación.

### Severity: Critical

---

### Root Cause Analysis

**Pasos para reproducir:**
1. El usuario completa (o abandona/falla) el pago en la plataforma externa.
2. La plataforma externa redirige al callback, disparando la Lambda `bw-002-SavePayment`.
3. La Lambda recibe el `transaction_id` y hace un `GET` al servicio externo para obtener el estado real del pago (`externalPaymentServiceUrl`).
4. **El problema**: la respuesta de ese `GET` se guarda en `response` pero **nunca se lee ni valida**.
5. Inmediatamente después, el código persiste el pago en DynamoDB con `payment_status: "success"` y `order_status: "paid"` hardcodeados, sin importar lo que el servicio externo haya respondido.

**Expected vs Actual:**

| Paso | Esperado | Actual |
|------|----------|--------|
| Verificar estado en servicio externo | Leer el cuerpo de la respuesta y verificar que el pago fue aprobado | `response` es obtenida pero su cuerpo nunca es leído ni evaluado |
| Guardar estado en DynamoDB | `payment_status` basado en el resultado real | Siempre guarda `"success"` hardcodeado |

**Ubicacion del bug:**

`src/internal_services/SavePayment.js:28-43`

```js
// Linea 28: se obtiene la respuesta PERO...
const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId), { ... });

// Linea 35-43: ...nunca se lee ni valida. Se guarda siempre como "success"
await docClient.send(new PutCommand({
    ...
    Item: {
        transaction_id: transactionId,
        payment_status: "success",   // <-- hardcodeado, no depende de `response`
        order_status: "paid",        // <-- hardcodeado
        ...
    }
}));
```

**Evidencia en logs:**

Los logs muestran errores recurrentes `TypeError: fetch failed` con `SocketError: other side closed` en `SavePayment.js:28`. Esto confirma que la llamada al servicio externo en esa linea esta fallando en multiples invocaciones. Cuando falla con un error de socket, la Lambda crashea y NO guarda nada. Pero cuando el servicio externo responde (aunque sea con un estado de pago fallido o pendiente), el codigo continua y guarda `"success"` de todas formas porque la respuesta nunca es inspeccionada.

**Flujo de ejecucion con valores hipoteticos:**

```
Input:  transaction_id = "TXN-9999"
GET /payments/TXN-9999 → responde { status: "failed", reason: "insufficient_funds" }
response.ok    = false   ← NUNCA SE VERIFICA
response.json() = { status: "failed" }  ← NUNCA SE LEE

DynamoDB.PutCommand({
  transaction_id: "TXN-9999",
  payment_status: "success",   ← INCORRECTO
  order_status: "paid"         ← INCORRECTO
})
```

---

### Solution

En `src/internal_services/SavePayment.js`, despues de la linea 33, leer y validar la respuesta del servicio externo antes de persistir. El `payment_status` y `order_status` deben derivarse del estado real que retorna el servicio externo, no ser valores fijos.

Pasos concretos:
1. Leer el cuerpo de `response` con `await response.json()`.
2. Verificar `response.ok` y el campo de estado dentro del cuerpo.
3. Si el pago no esta confirmado, guardar con `payment_status: "failed"` (o el estado correspondiente) y retornar un codigo de error apropiado en lugar de `200`.
4. Solo guardar `payment_status: "success"` si el servicio externo confirma el cobro exitoso.

Adicionalmente, los errores de socket (`fetch failed`) en linea 28 deben manejarse con un bloque `try/catch` para evitar que la Lambda crashee silenciosamente sin registrar el `transaction_id` afectado en el log de error.

# Total cost USD

0.18365925

# Execution time in seconds: 

67
