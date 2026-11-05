Tengo toda la evidencia necesaria. Aquí el análisis completo:

---

## Race Condition en transferencia de fondos: Balance negativo por falta de escritura condicional

### Summary: El balance del emisor puede volverse negativo bajo concurrencia porque la verificación de saldo y el débito no son atómicos.

### Severity: Critical

---

### Root Cause Analysis

**Arquitectura confirmada por `template.yaml`:**
- `TransferApiFunction` (POST `/transfer`) invoca DynamoDB directamente — **no delega en TransferProcessorFunction** a pesar de tener la política `LambdaInvokePolicy`.
- `TransferProcessorFunction` también accede DynamoDB directamente, sin trigger configurado (solo invocación programática).
- Ambas funciones ejecutan la **misma lógica de transferencia con el mismo defecto**.

**El defecto: TOCTOU (Time-of-Check / Time-of-Use)**

Los logs de `TransferProcessorFunction` confirman **20+ instancias Lambda concurrentes** procesando transferencias de `10 from ACC001 to ACC002` en el mismo instante (`2026-02-11T15:12:07`), con **IDs de transferencia distintos** (no son reintentos, son solicitudes separadas), y **todas reportan "completed successfully"**.

El flujo defectuoso en ambos archivos:

```
src/transfer-processor/app.ts  (idéntico en src/transfer-api/app.ts)

L32-36:  GetCommand → lee Balance de ACC001
L42-44:  GetCommand → lee Balance de ACC002
L57-60:  if (sourceBalance < amount) throw ...   // <-- verificacion en memoria con valor stale
L64-73:  UpdateCommand SET Balance = Balance - :amount  // <-- SIN ConditionExpression
L74-83:  UpdateCommand SET Balance = Balance + :amount
```

**Escenario de ejemplo con 3 Lambdas concurrentes, ACC001.Balance = 10:**

| Paso | Lambda 1 | Lambda 2 | Lambda 3 | ACC001.Balance real |
|------|----------|----------|----------|---------------------|
| GetCommand | lee 10 | lee 10 | lee 10 | 10 |
| Chequeo | 10 >= 10 OK | 10 >= 10 OK | 10 >= 10 OK | 10 |
| UpdateCommand -10 | ejecuta | — | — | **0** |
| UpdateCommand -10 | — | ejecuta | — | **-10** |
| UpdateCommand -10 | — | — | ejecuta | **-20** |

- ACC001 pasa de `10` a `-20`: se debitaron 30, solo había 10.
- ACC002 recibe `+30`: se **crearon 20 unidades de la nada**.
- DynamoDB aplica cada `Balance = Balance - :amount` atómicamente por separado, pero sin condición de guarda que impida que el saldo baje de cero.
- Ninguna invocación lanzó error, por eso los logs solo muestran `completed successfully`.

**Evidencia en logs** (15:12:07, burst de 20+ instancias):
```
Processing transfer 49131045...: 10 from ACC001 to ACC002
Processing transfer 92aac1ab...: 10 from ACC001 to ACC002
Processing transfer 7df13a08...: 10 from ACC001 to ACC002
... (20+ instancias simultáneas, todas sobre las mismas cuentas)
Transfer 49131045... completed successfully
Transfer 92aac1ab... completed successfully   ← todas exitosas, sin ConditionalCheckFailedException
```

**Ubicación exacta del defecto:**
- `src/transfer-processor/app.ts:64-73` — `UpdateCommand` débito sin `ConditionExpression`
- `src/transfer-api/app.ts:65-73` — mismo defecto (lógica duplicada)

---

### Solution

Agregar `ConditionExpression: 'Balance >= :amount'` al `UpdateCommand` de débito en **ambas funciones**. Esto convierte la verificación + débito en una operación atómica a nivel DynamoDB. Cuando la condición falla, DynamoDB lanza `ConditionalCheckFailedException`, que debe capturarse y traducirse a error de "saldo insuficiente" (no reintentar).

```typescript
// src/transfer-processor/app.ts  y  src/transfer-api/app.ts — mismo cambio en ambos
await docClient.send(new UpdateCommand({
    TableName: TABLE_NAME,
    Key: { AccountId: sourceAccountId },
    UpdateExpression: 'SET Balance = Balance - :amount, HashKey = :hash',
    ConditionExpression: 'Balance >= :amount',   // <-- AGREGAR ESTA LÍNEA
    ExpressionAttributeValues: {
        ':amount': amount,
        ':hash': newSourceHash,
    },
}));
```

Adicionalmente, la función `generateKeyHash()` genera y almacena **40 KB de datos aleatorios** en cada transacción. Esto no causa el problema de saldo, pero incrementa significativamente la latencia y el costo de escritura en DynamoDB bajo carga concurrente, empeorando la ventana de la condición de carrera.

# Total cost USD

0.73827125

# Execution time in seconds: 

184
