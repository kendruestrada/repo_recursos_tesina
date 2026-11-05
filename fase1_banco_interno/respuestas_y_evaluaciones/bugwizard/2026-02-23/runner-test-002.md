## Análisis del Ticket de Soporte

**Ticket:** Algunos pagos aparecen como 'exitosos' en nuestro sistema pero el dinero no fue debitado de la cuenta del cliente.

## Hallazgos en los logs

Al analizar los logs de CloudWatch, se identifican múltiples errores críticos que revelan la causa raíz del problema:

### Errores Recurrentes Detectados:
- **Error Principal**: `TypeError: fetch failed` con causa `SocketError: other side closed`
- **Frecuencia**: Múltiples ocurrencias a lo largo de varios días (16-19 Feb 2026)
- **Patrón**: Todos los errores ocurren en la línea 28 del archivo `SavePayment.js`
- **Direcciones IP afectadas**: 3.167.56.46, 3.167.56.70, 3.167.56.113 (servicios externos)

### Ejemplo de Error Típico:
```
2026-02-18T14:25:26.136Z ERROR Invoke Error 
{"errorType":"TypeError","errorMessage":"fetch failed",
"cause":{"errorType":"SocketError","errorMessage":"other side closed",
"code":"UND_ERR_SOCKET"}}
```

## Relación con el código fuente

### Análisis del flujo en `SavePayment.js`:

1. **Líneas 24-30**: Primera llamada fetch para obtener información del pago
2. **Líneas 32-40**: Guardado en DynamoDB (SIEMPRE se ejecuta)
3. **Líneas 47-53**: Segunda llamada fetch para confirmación externa

### Problema Identificado:
El código tiene un **fallo crítico en el manejo de errores**:

```javascript
// Línea 24-30: Primera llamada que puede fallar
const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId), {
    method: "GET",
    headers: {
        "Content-Type": "application/json"
    }
});

// Líneas 32-40: Se ejecuta SIEMPRE, incluso si la llamada anterior falló
await docClient.send(new PutCommand({
    TableName: tableName,
    Item: {
        transaction_id: transactionId,
        payment_status: "success", // ← PROBLEMA: Siempre marca como "success"
        order_status: "paid",
        processed_at: new Date().toISOString()
    }
}));
```

## Ejemplo de ejecución

**Escenario problemático:**
1. **Entrada**: `transaction_id: "TRX_CANARY_2718e1"`
2. **Paso 1**: Llamada a servicio externo falla (SocketError)
3. **Paso 2**: El código continúa ejecutándose sin validar la respuesta
4. **Paso 3**: Se guarda en DynamoDB con `payment_status: "success"`
5. **Paso 4**: Segunda llamada de confirmación también falla
6. **Resultado**: Pago marcado como exitoso en BD, pero nunca se procesó externamente

## Soluciones propuestas

### Solución 1: Validación de respuesta HTTP
```javascript
const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId), {
    method: "GET",
    headers: {
        "Content-Type": "application/json"
    }
});

// AGREGAR: Validación de respuesta
if (!response.ok) {
    throw new Error(`External service failed: ${response.status} ${response.statusText}`);
}

const paymentData = await response.json();
// Validar que el pago realmente fue procesado
if (paymentData.status !== 'completed') {
    throw new Error(`Payment not completed: ${paymentData.status}`);
}
```

### Solución 2: Manejo de errores con try-catch
```javascript
try {
    const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId));
    
    if (!response.ok) {
        throw new Error(`External service error: ${response.status}`);
    }
    
    const paymentData = await response.json();
    
    // Solo guardar si el pago fue exitoso externamente
    await docClient.send(new PutCommand({
        TableName: tableName,
        Item: {
            transaction_id: transactionId,
            payment_status: paymentData.status, // Usar estado real del servicio externo
            order_status: paymentData.status === 'completed' ? 'paid' : 'failed',
            processed_at: new Date().toISOString()
        }
    }));
    
} catch (error) {
    // Guardar como fallido si hay error
    await docClient.send(new PutCommand({
        TableName: tableName,
        Item: {
            transaction_id: transactionId,
            payment_status: "failed",
            order_status: "failed",
            error_message: error.message,
            processed_at: new Date().toISOString()
        }
    }));
    
    throw error; // Re-lanzar para que Lambda retorne error
}
```

### Solución 3: Configuración de red y timeouts
```javascript
const response = await fetch(externalPaymentServiceUrl.replace(":id", transactionId), {
    method: "GET",
    headers: {
        "Content-Type": "application/json"
    },
    timeout: 30000, // 30 segundos timeout
    retry: 3 // Reintentos automáticos
});
```

### Recomendación Inmediata:
1. **Implementar validación de respuesta HTTP** antes de guardar en DynamoDB
2. **Agregar manejo de errores** con try-catch
3. **Revisar transacciones existentes** marcadas como "success" para identificar falsos positivos
4. **Implementar logging detallado** del estado real del servicio externo

La causa raíz es que el sistema guarda el pago como exitoso independientemente del resultado de la llamada al servicio externo, debido a la falta de validación de la respuesta HTTP y manejo de errores.