## Bug: Compra fallida por dirección nula propagada silenciosamente

### Summary: `validate-address` enmascara un error del proveedor externo devolviendo HTTP 200 con `address: null`, lo que provoca que `process-purchase` rechace la compra con un 400.

### Severity: High

---

### Root Cause Analysis

**Flujo de ejecucion con el bug:**

1. El frontend envia `{name, email, address}` a `/validate-address`.
2. `validate-address` llama al servicio externo (`VALIDATION_SERVICE_URL`).
3. Si el servicio externo responde con un status distinto de 200, se ejecuta el bloque de error en `validate-address/index.js:17-27`.
4. **Problema**: ese bloque retorna `statusCode: 200` con `address: null` en el cuerpo.
5. El frontend evalua `res.status === 200` → verdadero → almacena `s = { name, email, address: null }` y habilita el boton "Complete Purchase".
6. El frontend llama a `/process-purchase` con `{ name, email, address: null }`.
7. `process-purchase/index.js:12` evalua `!data.address` → `null` es falsy → retorna HTTP 400 con "Invalid data context".
8. El frontend recibe 400, no muestra ningun mensaje al usuario. La compra falla silenciosamente.

**Expected vs. Actual:**

| | Esperado | Real |
|---|---|---|
| Fallo en proveedor externo | Retornar error al frontend (ej. 502/503) | Retorna HTTP 200 con `address: null` |
| Frontend al recibir fallo de validacion | Mostrar error, deshabilitar "Complete Purchase" | Habilita el boton, muestra "Data synchronized." |
| `/process-purchase` | Recibir direccion valida | Recibe `address: null`, rechaza con 400 |

**Ubicacion del bug:**

```
src/validate-address/index.js  lineas 17-27
```

El bloque condicional del error:

```js
// validate-address/index.js:17-27
if (audit.status !== 200) {
    console.error(`External provider error: ${audit.status} - Invalid address format`);
    
    const response = {
        statusCode: 200,           // <-- ERROR: deberia ser un codigo de error (ej. 502)
        body: JSON.stringify({ success: true, data: { name, email, address: null } })
        //                                                            ^^^^ dato corrupto propagado
    };
    return response;
}
```

---

### Solution

El fix debe estar en `src/validate-address/index.js`. El bloque de error debe retornar un codigo HTTP de error (no 200) para que el frontend lo detecte correctamente:

```js
if (audit.status !== 200) {
    console.error(`External provider error: ${audit.status} - Invalid address format`);
    return {
        statusCode: 502,
        headers: { "Access-Control-Allow-Origin": "*", "Content-Type": "application/json" },
        body: JSON.stringify({ success: false, error: "Address validation service unavailable" })
    };
}
```

Adicionalmente, el frontend (`frontend/index.html:26`) debe manejar el caso de error en la validacion para evitar habilitar el boton con datos invalidos:

```js
if (res.status === 200 && r.data && r.data.address) {
    s = r.data;
    document.getElementById('b').disabled = false;
    document.getElementById('o').innerText = 'Data synchronized.';
} else {
    document.getElementById('o').innerText = 'Address validation failed. Please try again.';
}
```

# Total cost USD

0.22795250000000006

# Execution time in seconds: 

46
