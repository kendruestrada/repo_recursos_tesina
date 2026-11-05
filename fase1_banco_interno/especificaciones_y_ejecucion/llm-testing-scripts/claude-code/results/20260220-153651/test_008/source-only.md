## Analisis de causa raiz: API Bancaria - Multiples Errores en Codigo Fuente

---

## [Bug 1]: Condicion de Carrera TOCTOU en Operaciones de Transferencia
### Summary: La logica de transferencia lee el saldo y luego lo actualiza sin garantia de atomicidad, permitiendo sobregiros en accesos concurrentes.
### Severity: Critical

### Root Cause Analysis

**Pasos para reproducir:**
1. Cuenta A tiene saldo = 100
2. Dos solicitudes concurrentes intentan transferir 80 cada una desde Cuenta A
3. Ambas ejecutan `GetCommand` y leen `Balance = 100`
4. Ambas pasan la validacion `sourceBalance < amount` (100 >= 80)
5. Ambas ejecutan `UpdateCommand` con `Balance = Balance - :amount`
6. Resultado final: `Balance = 100 - 80 - 80 = -60`

**Expected vs Actual:**
- Esperado: Segunda transferencia rechazada con "Insufficient balance"
- Actual: Ambas transferencias proceden, el saldo queda negativo

**Ubicacion del bug:**

`src/transfer-api/app.ts:65-73` y `src/transfer-processor/app.ts:64-72`

```typescript
// GetCommand (lectura) sin bloqueo
const sourceAccount = await docClient.send(new GetCommand(...));
const sourceBalance = sourceAccount.Item.Balance || 0;

if (sourceBalance < amount) { /* check */ }

// UpdateCommand (escritura) sin ConditionExpression
await docClient.send(new UpdateCommand({
    UpdateExpression: 'SET Balance = Balance - :amount, HashKey = :hash',
    ExpressionAttributeValues: { ':amount': amount, ':hash': newSourceHash },
    // FALTA: ConditionExpression: 'Balance >= :amount'
}));
```

### Solution
Agregar `ConditionExpression` en el `UpdateCommand` de la cuenta origen:

```typescript
ConditionExpression: 'Balance >= :amount',
```

Esto hace el check-and-update atomico en DynamoDB, eliminando el TOCTOU.

---

## [Bug 2]: `TransferProcessorFunction` Nunca Es Invocada (Codigo Muerto)
### Summary: `TransferApiFunction` reimplementa la logica de transferencia en vez de delegar a `TransferProcessorFunction`, dejando esta ultima como codigo muerto.
### Severity: High

### Root Cause Analysis

**Evidencia en `template.yaml`:**
- Linea 171-172: `TransferApiFunction` tiene `LambdaInvokePolicy` para `TransferProcessorFunction`
- Linea 179: `TRANSFER_PROCESSOR_FUNCTION: !Ref TransferProcessorFunction` configurado como variable de entorno

**Evidencia en el codigo:**

`src/transfer-api/app.ts:1-4` — no importa `LambdaClient` ni `InvokeCommand`, y en ningun lugar usa `process.env.TRANSFER_PROCESSOR_FUNCTION`.

En cambio, implementa su propia funcion `processTransfer()` local (lineas 25-117) que duplica exactamente la logica de `src/transfer-processor/app.ts`.

**Expected vs Actual:**
- Esperado: `TransferApiFunction` invoca `TransferProcessorFunction` via Lambda SDK para cada transferencia
- Actual: `TransferApiFunction` procesa las transferencias directamente; `TransferProcessorFunction` nunca es llamada

**Consecuencias:**
- Cualquier corrección aplicada a `transfer-processor/app.ts` no tiene efecto en produccion
- La politica `LambdaInvokePolicy` y la variable `TRANSFER_PROCESSOR_FUNCTION` son recursos desperdiciados
- Doble mantenimiento: la misma logica existe en dos archivos desincronizados

### Solution
`transfer-api/app.ts` debe invocar `TransferProcessorFunction` usando `LambdaClient`:

```typescript
import { LambdaClient, InvokeCommand } from '@aws-sdk/client-lambda';
const lambdaClient = new LambdaClient({});
const PROCESSOR_FN = process.env.TRANSFER_PROCESSOR_FUNCTION || '';

// En lugar de processTransfer(transfer) local:
await lambdaClient.send(new InvokeCommand({
    FunctionName: PROCESSOR_FN,
    Payload: Buffer.from(JSON.stringify(transfer)),
}));
```

---

## [Bug 3]: `HashKey` de 40KB Expuesto en Endpoint GET /account
### Summary: El endpoint get-account retorna el item completo de DynamoDB incluyendo el campo `HashKey` de 40,960 caracteres, exponiendo datos internos al cliente.
### Severity: Medium

### Root Cause Analysis

**Ubicacion:** `src/get-account/app.ts:33-36`

```typescript
return {
    statusCode: 200,
    body: JSON.stringify(result.Item), // retorna TODO el item, incluyendo HashKey
};
```

`HashKey` es un campo interno de seguridad (hash SHA256 repetido 640 veces = 40,960 caracteres) generado por `generateKeyHash()` en `src/create-account/app.ts:11-16`. No es un dato destinado al consumidor de la API.

**Impacto:**
- Cada respuesta GET pesa ~41KB innecesariamente
- Con `MemorySize: 128MB` y Lambda, esto incrementa latencia y costo
- El campo es un detalle de implementacion interna que no deberia ser visible

### Solution
Proyectar solo los campos necesarios en la respuesta:

```typescript
const { AccountId, Balance } = result.Item;
return {
    statusCode: 200,
    body: JSON.stringify({ AccountId, Balance }),
};
```

---

## Resumen de Hallazgos

| # | Archivo | Linea | Tipo | Severidad |
|---|---------|-------|------|-----------|
| 1 | `transfer-api/app.ts` | 65-73 | TOCTOU / Race condition | Critical |
| 1 | `transfer-processor/app.ts` | 64-72 | TOCTOU / Race condition | Critical |
| 2 | `transfer-api/app.ts` | 1-190 | Arquitectura / Codigo muerto | High |
| 3 | `get-account/app.ts` | 35 | Exposicion de datos internos | Medium |

# Total cost USD

0.3692455

# Execution time in seconds: 

86
