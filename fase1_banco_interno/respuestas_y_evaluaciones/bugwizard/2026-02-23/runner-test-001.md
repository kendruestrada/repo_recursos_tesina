## Análisis del Ticket de Soporte

**Ticket:** Al presionar el botón 'Comprar', la aplicación no hace nada. El botón no responde y no aparece ningún error.

## Hallazgos en los logs

Analizando los logs de CloudWatch, se identifican patrones consistentes de errores:

1. **Error recurrente en ProcessPurchase:**
   ```
   ERROR Purchase rejected: shipping address is missing or null
   ```

2. **Datos recibidos con address: null:**
   ```
   INFO ProcessPurchase received customer data: {"name":"Maximiliano Lopez","email":"usuario@example.com","address":null}
   ```

3. **Respuestas HTTP 400:** El sistema está devolviendo códigos de error 400 (Bad Request) debido a datos inválidos.

## Relación con el código fuente

### Problema identificado en `validate-address/index.js`:

```javascript
if (audit.status !== 200) {
    console.error(`External provider error: ${audit.status} - Invalid address format`);
    
    const response = {
        statusCode: 200,  // ← PROBLEMA: Devuelve 200 aunque hay error
        headers: { "Access-Control-Allow-Origin": "*", "Content-Type": "application/json" },
        body: JSON.stringify({ success: true, data: { name, email, address: null } }) // ← address: null
    };
    
    console.log(`Sync status: ${response.statusCode}`);
    return response;
}
```

### Problema en `process-purchase/index.js`:

```javascript
if (!data || !data.address) {
    console.error("Purchase rejected: shipping address is missing or null");
    return {
        statusCode: 400,  // ← Devuelve error 400
        headers: { "Access-Control-Allow-Origin": "*", "Content-Type": "application/json" },
        body: JSON.stringify({ 
            success: false, 
            error: "Invalid data context",
            receivedAddress: data ? data.address : "undefined"
        })
    };
}
```

### Problema en el frontend `index.html`:

```javascript
document.getElementById('b').addEventListener('click', async () => {
    document.getElementById('o').innerText = 'Processing...';
    const res = await fetch(`${API}/process-purchase`, { method: 'POST', body: JSON.stringify(s) });
    if (res.status === 200) {  // ← Solo maneja status 200
        const r = await res.json();
        document.getElementById('o').innerHTML = '<h2>Order: ' + r.data.orderId + '</h2>';
    }
    // ← NO HAY MANEJO DE ERRORES para status !== 200
});
```

## Ejemplo de ejecución

**Flujo actual problemático:**

1. **Usuario ingresa datos:** name="Juan", email="juan@test.com", address="Calle 123"
2. **validate-address falla:** El servicio externo devuelve status !== 200
3. **validate-address responde:** `{ success: true, data: { name: "Juan", email: "juan@test.com", address: null } }`
4. **Frontend recibe:** Status 200, habilita botón "Complete Purchase"
5. **Usuario presiona "Complete Purchase"**
6. **process-purchase recibe:** `{ name: "Juan", email: "juan@test.com", address: null }`
7. **process-purchase valida:** `!data.address` es true, devuelve status 400
8. **Frontend recibe:** Status 400, pero NO tiene manejo de errores
9. **Resultado:** El botón parece no responder, no se muestra ningún mensaje

## Soluciones propuestas

### Solución 1: Corregir el manejo de errores en el frontend

```javascript
document.getElementById('b').addEventListener('click', async () => {
    document.getElementById('o').innerText = 'Processing...';
    const res = await fetch(`${API}/process-purchase`, { method: 'POST', body: JSON.stringify(s) });
    
    if (res.status === 200) {
        const r = await res.json();
        document.getElementById('o').innerHTML = '<h2>Order: ' + r.data.orderId + '</h2>';
    } else {
        // AGREGAR MANEJO DE ERRORES
        const errorData = await res.json();
        document.getElementById('o').innerHTML = '<div style="color: red;">Error: ' + 
            (errorData.error || 'Purchase failed') + '</div>';
    }
});
```

### Solución 2: Corregir la validación de dirección

```javascript
// En validate-address/index.js
if (audit.status !== 200) {
    console.error(`External provider error: ${audit.status} - Invalid address format`);
    
    return {
        statusCode: 400,  // Cambiar a 400 para indicar error
        headers: { "Access-Control-Allow-Origin": "*", "Content-Type": "application/json" },
        body: JSON.stringify({ 
            success: false, 
            error: "Address validation failed. Please verify your address." 
        })
    };
}
```

### Solución 3: Mejorar la validación en el frontend

```javascript
document.getElementById('f').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const res = await fetch(`${API}/validate-address`, {
        method: 'POST',
        body: JSON.stringify({
            name: document.getElementById('n').value, 
            email: document.getElementById('e').value, 
            address: document.getElementById('a').value
        })
    });
    
    const r = await res.json();
    if (res.status === 200 && r.success && r.data.address) {  // Verificar que address no sea null
        s = r.data;
        document.getElementById('b').disabled = false;
        document.getElementById('o').innerText = 'Data synchronized.';
    } else {
        document.getElementById('o').innerHTML = '<div style="color: red;">Address validation failed. Please check your address.</div>';
        document.getElementById('b').disabled = true;
    }
});
```

**Recomendación:** Implementar las tres soluciones para una experiencia de usuario completa y robusta.