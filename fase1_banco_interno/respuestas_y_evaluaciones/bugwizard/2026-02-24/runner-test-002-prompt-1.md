## Análisis del Ticket de Soporte

**Ticket:** Algunos pagos aparecen como 'exitosos' en nuestro sistema pero el dinero no fue debitado de la cuenta del cliente.

## Hallazgos en los logs

Al analizar los logs proporcionados, se identificó un patrón crítico de errores que se repite consistentemente:

1. **Error recurrente de conexión**: `TypeError: fetch failed` con causa `SocketError: other side closed`
2. **Patrón temporal**: Los errores ocurren sistemáticamente cada vez que se intenta procesar un callback de pago
3. **Secuencia típica observada**:
   ```
   INFO	PAYMENT_CALLBACK_RECEIVED { transaction_id: 'TRX_CANARY_xxx' }
   ERROR	Invoke Error TypeError: fetch failed
   ```

4. **Detalles técnicos del error**:
   - Error: `UND_ERR_SOCKET` - "other side closed"
   - Direcciones IP afectadas: `3.167.56.113`, `3.167.56.70`, `3.167.56.46`
   - Puerto: 443 (HTTPS)
   - El socket se cierra inesperadamente durante la comunicación

## Relación con el código fuente

Analizando el archivo `SavePayment.js`, se identifica la **causa raíz** del problema:

### Problema Principal: Orden incorrecto de operaciones

```javascript
// LÍNEA 28: Primera llamada fetch (obtener datos del pago)
const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId), {
    method: "GET",
    headers: {
        "Content-Type": "application/json"
    }
});

// LÍNEAS 30-38: Guardado en base de datos LOCAL (se ejecuta SIEMPRE)
await docClient.send(new PutCommand({
    TableName: tableName,
    Item: {
        transaction_id: transactionId,
        payment_status: "success",  // ← PROBLEMA: Se marca como exitoso sin validar
        order_status: "paid",
        processed_at: new Date().toISOString()
    }
}));

// LÍNEAS 44-49: Segunda llamada fetch (confirmación externa)
const confirmationResponse = await fetch(externalPaymentServiceConfirmationUrl.replace(":id", transactionId), {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    }
});
```

### Problemas identificados:

1. **Falta de validación de la primera respuesta**: El código no verifica si la primera llamada `fetch` fue exitosa
2. **Guardado prematuro**: Se guarda en la base de datos como "success" sin confirmar que el servicio externo procesó correctamente el pago
3. **Manejo inadecuado de errores**: Si cualquiera de las llamadas `fetch` falla, el registro ya quedó marcado como exitoso en la base de datos

## Ejemplo de ejecución

**Escenario problemático actual:**
```javascript
// 1. Se recibe callback: transaction_id = "TRX_CANARY_aa44a9"
// 2. Primera fetch falla (SocketError: other side closed)
// 3. Se ejecuta el guardado en DB:
//    {
//      transaction_id: "TRX_CANARY_aa44a9",
//      payment_status: "success",  // ← INCORRECTO
//      order_status: "paid"
//    }
// 4. Segunda fetch también falla
// 5. Función termina con error, pero el pago ya está marcado como exitoso
```

## Soluciones propuestas

### Solución 1: Validación y orden correcto de operaciones

```javascript
exports.handler = async (event) => {
    console.info("RAW_EVENT", JSON.stringify(event));

    const transactionId = event.queryStringParameters?.transaction_id;
    const tableName = process.env.TABLE_NAME;

    if (!transactionId) {
        console.error("MISSING_TRANSACTION_ID");
        return {
            statusCode: 400,
            body: JSON.stringify({ error: "transaction_id is required" })
        };
    }

    console.info("PAYMENT_CALLBACK_RECEIVED", { transaction_id: transactionId });

    try {
        // 1. Obtener datos del pago externo
        const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId), {
            method: "GET",
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(`Payment service returned ${response.status}: ${response.statusText}`);
        }

        const paymentData = await response.json();
        
        // 2. Validar que el pago fue realmente procesado
        if (paymentData.status !== 'completed' || !paymentData.debited) {
            throw new Error(`Payment not completed or not debited: ${JSON.stringify(paymentData)}`);
        }

        // 3. Confirmar con el servicio externo
        const confirmationResponse = await fetch(externalPaymentServiceConfirmationUrl.replace(":id", transactionId), {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!confirmationResponse.ok) {
            throw new Error(`Confirmation failed ${confirmationResponse.status}: ${confirmationResponse.statusText}`);
        }

        // 4. SOLO AHORA guardar como exitoso en la base de datos
        await docClient.send(new PutCommand({
            TableName: tableName,
            Item: {
                transaction_id: transactionId,
                payment_status: "success",
                order_status: "paid",
                processed_at: new Date().toISOString(),
                external_confirmation: true
            }
        }));

        console.info("LOCAL_PAYMENT_PERSISTED", { transaction_id: transactionId });

        return {
            statusCode: 200,
            body: JSON.stringify({
                transaction_id: transactionId,
                db_status: "success",
            })
        };

    } catch (error) {
        console.error("PAYMENT_PROCESSING_ERROR", { 
            transaction_id: transactionId, 
            error: error.message 
        });

        // Guardar como fallido
        await docClient.send(new PutCommand({
            TableName: tableName,
            Item: {
                transaction_id: transactionId,
                payment_status: "failed",
                order_status: "pending",
                processed_at: new Date().toISOString(),
                error_message: error.message
            }
        }));

        return {
            statusCode: 500,
            body: JSON.stringify({
                transaction_id: transactionId,
                db_status: "failed",
                error: error.message
            })
        };
    }
};
```

### Solución 2: Implementar reintentos y timeout

```javascript
// Agregar configuración de timeout y reintentos
const fetchWithRetry = async (url, options, maxRetries = 3, timeout = 10000) => {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeout);
            
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            console.warn(`Fetch attempt ${i + 1} failed:`, error.message);
            if (i === maxRetries - 1) throw error;
            await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1))); // Backoff
        }
    }
};
```

### Solución 3: Implementar estado intermedio

Modificar el esquema de la base de datos para incluir estados intermedios:
- `pending`: Callback recibido, procesando
- `verified`: Pago verificado externamente
- `confirmed`: Confirmación enviada
- `success`: Proceso completado exitosamente
- `failed`: Error en cualquier paso

La **causa raíz** del problema es que el sistema marca los pagos como exitosos antes de verificar que realmente fueron procesados por el servicio externo, debido a errores de conectividad que impiden la validación adecuada.