Con todos los datos disponibles (logs + código fuente), puedo presentar el análisis completo.

---

## [Flujo de Compra Bloqueado]: El botón "Complete Purchase" no completa la compra y no muestra error alguno

### Summary: La Lambda `validate-address` enmascara un error externo retornando HTTP 200 con `address: null`, lo que provoca que `process-purchase` rechace la solicitud con HTTP 400 y el frontend quede congelado en "Processing..." sin retroalimentación al usuario.

### Severity: High

---

### Root Cause Analysis

**Cadena de fallo (paso a paso):**

**1. Fallo en el proveedor externo de validacion** — `validate-address/index.js:6`

`VALIDATION_SERVICE_URL` retorna HTTP 400. Los logs de `/aws/lambda/t001-validate-address` lo confirman en TODAS las invocaciones:

```
ERROR  External provider error: 400 - Invalid address format
INFO   Sync status: 200
```

**2. Bug principal: validate-address enmascara el error** — `validate-address/index.js:17-28`

Cuando `audit.status !== 200`, en lugar de retornar un error al cliente, el codigo retorna HTTP 200 con `address: null`:

```js
// validate-address/index.js:17-28
if (audit.status !== 200) {
    console.error(`External provider error: ${audit.status} - Invalid address format`);
    const response = {
        statusCode: 200,                                     // <-- HTTP 200 fraudulento
        body: JSON.stringify({ success: true, data: { name, email, address: null } })  // <-- address: null
    };
    return response;
}
```

**3. El frontend almacena datos corrompidos** — `frontend/index.html:26-30`

El frontend interpreta el HTTP 200 como exito, guarda `s = r.data` (que contiene `address: null`) y habilita el boton "Complete Purchase":

```js
if (res.status === 200) {
    s = r.data;   // s = { name, email, address: null }
    document.getElementById('b').disabled = false;
    document.getElementById('o').innerText = 'Data synchronized.';
}
```

Los logs de `/aws/lambda/t001-process-purchase` confirman que siempre llega con `address: null`:

```
INFO  ProcessPurchase received customer data: {"name":"Maximiliano Lopez","email":"usuario@example.com","address":null}
```

**4. process-purchase rechaza la solicitud con HTTP 400** — `process-purchase/index.js:12-23`

La validacion detecta el `address` nulo y retorna HTTP 400:

```js
if (!data || !data.address) {
    console.error("Purchase rejected: shipping address is missing or null");
    return { statusCode: 400, ... };
}
```

**5. El frontend no maneja el error — UI queda congelada** — `frontend/index.html:33-40`

El handler del boton "Complete Purchase" solo reacciona ante HTTP 200. Si la respuesta es 400, no ejecuta nada, dejando el texto "Processing..." sin actualizarse ni mostrar error:

```js
document.getElementById('b').addEventListener('click', async () => {
    document.getElementById('o').innerText = 'Processing...';
    const res = await fetch(`${API}/process-purchase`, { method: 'POST', body: JSON.stringify(s) });
    if (res.status === 200) {          // 400 no entra aqui
        // ... muestra orderId
    }
    // sin else: no hay manejo de error -> UI congelada
});
```

**Steps to reproduce:**

1. Abrir la pagina de checkout
2. Ingresar nombre, email y una direccion valida
3. Hacer click en "Verify"
4. El boton "Complete Purchase" se habilita y muestra "Data synchronized." (apariencia de exito)
5. Hacer click en "Complete Purchase"
6. La UI muestra "Processing..." y nunca avanza — sin error visible

**Expected vs Actual:**

| | Esperado | Actual |
|---|---|---|
| Al fallar validacion externa | Retornar HTTP 400/500 al frontend | Retorna HTTP 200 con `address: null` |
| Boton habilitado | Solo si `address` es valido | Se habilita con datos corrompidos |
| Al fallar compra (HTTP 400) | Mostrar mensaje de error al usuario | UI queda congelada en "Processing..." |

---

### Solution

Hay dos puntos de correccion independientes:

**Correccion 1 (causa raiz) — `validate-address/index.js:17-28`**

Cuando el proveedor externo falla, retornar un HTTP de error en lugar de HTTP 200 con datos corrompidos:

```js
if (audit.status !== 200) {
    console.error(`External provider error: ${audit.status} - Invalid address format`);
    return {
        statusCode: 502,   // o 400 segun semantica deseada
        headers: { "Access-Control-Allow-Origin": "*", "Content-Type": "application/json" },
        body: JSON.stringify({ success: false, error: "Address validation failed" })
    };
}
```

**Correccion 2 (manejo de error en UI) — `frontend/index.html:33-40`**

Agregar un `else` para manejar la respuesta de error de `process-purchase` e informar al usuario:

```js
if (res.status === 200) {
    const r = await res.json();
    document.getElementById('o').innerHTML = '<h2>Order: ' + r.data.orderId + '</h2>';
} else {
    document.getElementById('o').innerText = 'Purchase failed. Please try again.';
}
```

# Total cost USD

0.708001

# Execution time in seconds: 

89
