Con los logs y el código fuente analizados, ya tengo suficiente información para el diagnóstico completo.

---

## Transferencia Bancaria: Dinero Desaparece en Operaciones Concurrentes

### Summary: Las operaciones de débito y crédito se ejecutan en dos escrituras DynamoDB separadas y no transaccionales, sin bloqueo optimista, lo que provoca pérdida de fondos en escenarios de ejecución concurrente.

### Severity: Critical

---

### Root Cause Analysis

**Pasos para reproducir**

1. Enviar 30+ requests de transferencia de ACC001 → ACC002 simultáneamente (exactamente el patrón observado en logs).
2. Cada Lambda realiza `GetCommand` para leer el saldo actual.
3. Cada Lambda valida el saldo con un valor posiblemente desactualizado (lectura sucia).
4. Cada Lambda ejecuta `UpdateCommand` para debitar ACC001.
5. Lambda falla, timeout, o se interrumpe entre el débito y el crédito.
6. ACC002 nunca recibe los fondos.

---

**Evidencia en los logs**

Los logs de `TransferApiFunction` muestran decenas de invocaciones Lambda concurrentes procesando la misma ruta `ACC001 → ACC002` dentro de una ventana de ~500ms:

```
13:00:32.385 - Processing transfer 13e3ab6a: 10 from ACC001 to ACC002
13:00:32.418 - Processing transfer ba2893e9: 10 from ACC001 to ACC002
13:00:32.423 - Processing transfer 0fcac7f7: 10 from ACC001 to ACC002
13:00:32.435 - Processing transfer eacafdb1: 10 from ACC001 to ACC002
13:00:32.437 - Processing transfer 72c58d35: 10 from ACC001 to ACC002
... (50+ invocaciones en la misma ventana)
```

Adicionalmente, `TransferProcessorFunction` tiene **cero registros** en CloudWatch, confirmando que ese processor nunca fue invocado.

---

**Expected vs. Actual**

| Aspecto | Esperado | Actual |
|---|---|---|
| Atomicidad debit/credit | Una transacción atómica | Dos `UpdateCommand` independientes |
| Protección de balance | Condición verificada en DynamoDB | Validación en memoria con lectura obsoleta |
| Visibilidad del saldo durante transferencia | Cuentas "congeladas" (locked) durante la operación | No hay bloqueo; lecturas concurrentes ven valores inconsistentes |

---

**Ubicación del bug**

Dos archivos presentan el mismo patrón defectuoso:

- `src/transfer-api/app.ts:65-83` — función `processTransfer`
- `src/transfer-processor/app.ts:64-82` — función `handler`

**Problema 1 — Split transaction (causa primaria de la desaparición de dinero)**

```typescript
// transfer-api/app.ts:65-73
await docClient.send(new UpdateCommand({   // DÉBITO: dinero sale de ACC001
    UpdateExpression: 'SET Balance = Balance - :amount, HashKey = :hash',
    ...
}));

// SI OCURRE UN FALLO AQUÍ → EL DINERO YA SALIÓ PERO NO ENTRÓ
// (Lambda timeout, error de red, excepción no capturada)

// transfer-api/app.ts:75-83
await docClient.send(new UpdateCommand({   // CRÉDITO: nunca ejecutado
    UpdateExpression: 'SET Balance = Balance + :amount, HashKey = :hash',
    ...
}));
```

No existe ningún mecanismo de compensación ni rollback si el segundo `UpdateCommand` falla. El dinero debitado de ACC001 desaparece del sistema.

**Problema 2 — Lectura sucia del balance (causa del overdraft concurrente)**

```typescript
// transfer-api/app.ts:33-36  (lectura NO transaccional)
const sourceAccount = await docClient.send(new GetCommand({ ... }));

// transfer-api/app.ts:58-60  (validación sobre valor obsoleto)
const sourceBalance = sourceAccount.Item.Balance || 0;
if (sourceBalance < amount) { throw ... }

// transfer-api/app.ts:65-73  (escritura SIN ConditionExpression)
await docClient.send(new UpdateCommand({
    UpdateExpression: 'SET Balance = Balance - :amount, ...',
    // Sin: ConditionExpression: 'Balance >= :amount'
}));
```

50 Lambdas concurrentes leen el mismo saldo (ej: `1000`), todas pasan la validación en memoria, y todas ejecutan el débito. El resultado es un overdraft donde el saldo puede quedar negativo.

---

### Solution

Reemplazar las dos escrituras independientes por una única operación `TransactWriteCommand` de DynamoDB que:

1. Verifica el saldo disponible **como condición atómica** en DynamoDB (`ConditionExpression: 'Balance >= :amount'`).
2. Realiza el débito y el crédito en una sola transacción (ambas operaciones ocurren juntas o ninguna).

```typescript
import { TransactWriteCommand } from '@aws-sdk/lib-dynamodb';

await docClient.send(new TransactWriteCommand({
    TransactItems: [
        {
            Update: {
                TableName: TABLE_NAME,
                Key: { AccountId: sourceAccountId },
                UpdateExpression: 'SET Balance = Balance - :amount',
                ConditionExpression: 'Balance >= :amount',
                ExpressionAttributeValues: { ':amount': amount },
            },
        },
        {
            Update: {
                TableName: TABLE_NAME,
                Key: { AccountId: destAccountId },
                UpdateExpression: 'SET Balance = Balance + :amount',
                ExpressionAttributeValues: { ':amount': amount },
            },
        },
    ],
}));
```

Este cambio debe aplicarse en **ambos archivos**:
- `src/transfer-api/app.ts` — reemplazar líneas 65–83
- `src/transfer-processor/app.ts` — reemplazar líneas 64–82

Con esto se garantiza que: el saldo nunca entra en estado parcial visible externamente, el dinero no puede desaparecer entre el débito y el crédito, y múltiples Lambdas concurrentes no pueden overdraftear la cuenta porque la condición se evalúa atómicamente en DynamoDB.

# Total cost USD

0.6404005

# Execution time in seconds: 

95
