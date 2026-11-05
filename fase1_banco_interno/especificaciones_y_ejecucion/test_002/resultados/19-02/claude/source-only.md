## Bug Identificado: Respuesta del servicio externo ignorada antes de persistir la transaccion

### Summary: El resultado del servicio externo de pago no se valida antes de guardar la transaccion en DynamoDB, lo que causa que toda transaccion se persista siempre como exitosa.

### Severity: Critical

### Root Cause Analysis

**Pasos para reproducir:**
1. El endpoint `/payment-callback` recibe un `transaction_id` via query param.
2. Se realiza un `GET` a `externalPaymentServiceUrl` para consultar el estado real del pago (linea 28).
3. La respuesta (`response`) se almacena pero **nunca se lee ni se valida**.
4. Se escribe directamente en DynamoDB con `payment_status: "success"` y `order_status: "paid"` de forma hardcodeada (lineas 35-43).
5. Luego se llama al servicio de confirmacion.

**Esperado vs. Actual:**
- **Esperado:** El estado del pago guardado en DynamoDB debe reflejar lo que retorna el servicio externo (puede ser `failed`, `pending`, `declined`, etc.).
- **Actual:** Independientemente de la respuesta del servicio externo, la transaccion se guarda siempre con `payment_status: "success"` y `order_status: "paid"`.

**Ubicacion del bug:**
- Archivo: `src/internal_services/SavePayment.js`
- Lineas 28-43: la variable `response` se asigna en la linea 28 pero nunca se usa; el `PutCommand` que sigue usa valores estaticos en lugar de los datos de `response`.

```js
// linea 28: response se obtiene pero nunca se lee
const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId), { ... });

// lineas 35-43: siempre se graba "success"/"paid" sin importar lo que respondio el servicio
await docClient.send(new PutCommand({
    Item: {
        payment_status: "success",   // hardcodeado
        order_status: "paid",        // hardcodeado
    }
}));
```

### Solution

Leer el cuerpo de `response`, extraer el estado real del pago y usar esos valores al construir el `Item` del `PutCommand`. Ademas, verificar que `response.ok` sea `true` antes de persistir, y manejar el caso de error (retornar 502 o similar si el servicio externo falla). Solo despues de persistir correctamente el estado real debe llamarse al endpoint de confirmacion.

# Total cost USD

0.221141

# Execution time in seconds: 

45
