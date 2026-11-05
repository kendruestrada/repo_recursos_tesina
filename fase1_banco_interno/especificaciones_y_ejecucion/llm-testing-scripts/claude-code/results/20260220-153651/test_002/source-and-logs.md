---

## Pagos marcados como exitosos sin debito real en cuenta del cliente

### Summary
El sistema persiste el pago como `"success"` en DynamoDB **antes** de llamar al servicio de confirmacion externo, y **nunca valida** la respuesta de dicha confirmacion, la cual retorna HTTP 404 en el 100% de los casos segun los logs.

### Severity: Critical

---

### Root Cause Analysis

**Dos bugs combinados producen el problema:**

#### Bug 1 — Orden incorrecto y ausencia de validacion de la confirmacion (causa principal)
**Archivo**: `src/internal_services/SavePayment.js`

El flujo actual es:
1. Linea 28: GET al servicio externo (obtiene datos de la transaccion)
2. **Lineas 35–43: persiste en DynamoDB con `payment_status: "success"` y `order_status: "paid"` — incondicionalmente**
3. Lineas 49–54: POST al endpoint de confirmacion (el que realmente debita la cuenta)
4. Linea 55: loguea el status de la confirmacion pero **nunca lo evalua**
5. Lineas 60–66: retorna HTTP 200 con `db_status: "success"` — **siempre**, independientemente de lo que respondio la confirmacion

El codigo nunca ejecuta ninguna validacion sobre `confirmationResponse.status`. Si la confirmacion falla, el pago ya fue grabado en la base de datos como exitoso y la Lambda ya retorno 200. El debito nunca ocurrio.

**Flujo correcto esperado:**
1. GET externo → validar que la transaccion existe
2. POST confirmacion → este es el paso que ejecuta el debito
3. Solo si la confirmacion es exitosa → persistir en DynamoDB como "success"

#### Bug 2 — El endpoint de confirmacion retorna 404 en todos los llamados
Los logs muestran **447 de 447 respuestas de confirmacion con `{ status: 404, statusText: 'Not Found' }`**, desde el 11-feb-2026 hasta hoy. El endpoint configurado en `EXTERNAL_PAYMENT_SERVICE_CONFIRMATION_URL` no existe o la sustitucion de `:id` en la URL produce una ruta invalida. Esto significa que el debito **nunca se ha ejecutado** correctamente en todo el periodo relevante.

**Evidencia de logs:**
```
2026-02-11T21:42:53Z  CONFIRMATION_RESPONSE { status: 404, statusText: 'Not Found' }
2026-02-12T15:35:34Z  CONFIRMATION_RESPONSE { status: 404, statusText: 'Not Found' }
...  (447 ocurrencias, 100% de las llamadas)
```

#### Bug 3 — Falla intermitente en el GET inicial (efecto secundario)
En 17 invocaciones se registra `TypeError: fetch failed` con `SocketError: other side closed` en `SavePayment.js:28`. En estos casos la Lambda falla completamente y no graba nada, por lo que **no contribuyen** al problema de falsos positivos, pero indican inestabilidad en el servicio externo.

---

**Steps to reproduce:**
1. Invocar la Lambda con un `transaction_id` valido
2. La Lambda llama GET al servicio externo (linea 28)
3. La Lambda **escribe en DynamoDB como `success`** (lineas 35–43) sin esperar confirmacion
4. La Lambda llama POST a la URL de confirmacion (linea 49) — recibe HTTP 404
5. La Lambda retorna HTTP 200 con `db_status: "success"` — el debito nunca ocurrio

**Expected**: Solo grabar como exitoso si la confirmacion retorno HTTP 2xx  
**Actual**: Siempre graba como exitoso; ignora completamente el status de la confirmacion

**Location**: `src/internal_services/SavePayment.js`
- Lineas 35–43: persistencia prematura e incondicional
- Lineas 49–58: llamado a confirmacion sin validacion del resultado
- Lineas 60–66: respuesta siempre exitosa al caller

---

### Solution

**Correccion 1 — Reordenar el flujo e incorporar validacion de la confirmacion:**

```js
// 1. GET al servicio externo (ya existe, linea 28)
const response = await fetch(...);

// 2. Llamar a la confirmacion ANTES de persistir
const confirmationResponse = await fetch(externalPaymentServiceConfirmationUrl...);

// 3. Validar la respuesta de confirmacion
if (!confirmationResponse.ok) {
    console.error("CONFIRMATION_FAILED", {
        transaction_id: transactionId,
        status: confirmationResponse.status
    });
    return {
        statusCode: 502,
        body: JSON.stringify({ error: "Payment confirmation failed", status: confirmationResponse.status })
    };
}

// 4. Solo si la confirmacion fue exitosa, persistir en DynamoDB
await docClient.send(new PutCommand({ ... payment_status: "success" ... }));
```

**Correccion 2 — Verificar y corregir la URL de confirmacion:**
El valor de `EXTERNAL_PAYMENT_SERVICE_CONFIRMATION_URL` (variable de entorno) debe apuntar a un endpoint que exista. Verificar que el reemplazo de `:id` genere una URL valida. En el template SAM (`template.yaml`) revisar el valor configurado para esta variable. El 100% de llamadas con 404 indica un problema estructural en la URL, no un error puntual.

# Total cost USD

0.555956

# Execution time in seconds: 

97
