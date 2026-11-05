## Análisis del Ticket de Soporte Técnico

**Ticket:** Inconsistencia en las cantidades de transferencias, pérdida de dinero en el sistema bancario.

## Hallazgos en los logs

### Errores críticos identificados:

1. **Errores de permisos de DynamoDB masivos:**
```
AccessDeniedException: User: arn:aws:sts::123456789012:assumed-role/test-008-TransferApiFunctionRole-KKggZmYTrf5w/TransferApiFunction is not authorized to perform: dynamodb:GetItem on resource: arn:aws:dynamodb:us-east-1:123456789012:table/BankingTable because no identity-based policy allows the dynamodb:GetItem action
```

2. **Patrón de ejecución concurrente problemático:**
   - Múltiples transferencias simultáneas del mismo monto (10) entre las mismas cuentas (ACC001 → ACC002)
   - Timestamps muy cercanos sugieren condiciones de carrera
   - Ejemplo: `2026-02-11T18:19:16.198Z` a `2026-02-11T18:19:16.420Z` - múltiples transferencias en 222ms

3. **Transferencias exitosas mezcladas con fallos:**
   - Algunas transferencias se completan: "Transfer completed successfully"
   - Otras fallan por permisos, pero el dinero podría haberse debitado parcialmente

## Relación con el código fuente

### Problema principal identificado en `transfer-api/app.ts`:

```typescript
async function processTransfer(transfer: Transfer): Promise<any> {
    // ... código de validación ...
    
    // PROBLEMA 1: Operaciones no atómicas
    await docClient.send(new UpdateCommand({
        TableName: TABLE_NAME,
        Key: { AccountId: sourceAccountId },
        UpdateExpression: 'SET Balance = Balance - :amount, HashKey = :hash',
        ExpressionAttributeValues: {
            ':amount': amount,
            ':hash': newSourceHash,
        },
    }));

    // PROBLEMA 2: Si falla aquí, el dinero ya se debitó de la cuenta origen
    await docClient.send(new UpdateCommand({
        TableName: TABLE_NAME,
        Key: { AccountId: destAccountId },
        UpdateExpression: 'SET Balance = Balance + :amount, HashKey = :hash',
        ExpressionAttributeValues: {
            ':amount': amount,
            ':hash': newDestHash,
        },
    }));
}
```

### Problemas identificados:

1. **Falta de transaccionalidad:** Las operaciones de débito y crédito son independientes
2. **Sin control de concurrencia:** No hay locks ni condiciones para evitar race conditions
3. **Manejo de errores incompleto:** Si falla la segunda operación, la primera ya se ejecutó
4. **Permisos inconsistentes:** El rol no tiene permisos para `GetItem` pero sí para `UpdateCommand`

## Ejemplo de ejecución problemática

```typescript
// Escenario: 3 transferencias concurrentes de 10 cada una
// Balance inicial ACC001: 1000

// Transferencia 1: Lee balance = 1000, debita 10 → Balance = 990
// Transferencia 2: Lee balance = 1000 (antes del commit de T1), debita 10 → Balance = 980  
// Transferencia 3: Lee balance = 1000 (antes del commit de T1,T2), debita 10 → Balance = 970

// Resultado: Se debitaron 30, pero cada transferencia "vio" balance = 1000
// Si alguna falla en el crédito, el dinero se pierde
```

## Soluciones propuestas

### Solución 1: Implementar transacciones DynamoDB
```typescript
import { TransactWriteCommand } from '@aws-sdk/lib-dynamodb';

const transactionItems = [
    {
        Update: {
            TableName: TABLE_NAME,
            Key: { AccountId: sourceAccountId },
            UpdateExpression: 'SET Balance = Balance - :amount, HashKey = :hash',
            ConditionExpression: 'Balance >= :amount', // Validación atómica
            ExpressionAttributeValues: {
                ':amount': amount,
                ':hash': newSourceHash,
            },
        }
    },
    {
        Update: {
            TableName: TABLE_NAME,
            Key: { AccountId: destAccountId },
            UpdateExpression: 'SET Balance = Balance + :amount, HashKey = :hash',
            ExpressionAttributeValues: {
                ':amount': amount,
                ':hash': newDestHash,
            },
        }
    }
];

await docClient.send(new TransactWriteCommand({
    TransactItems: transactionItems
}));
```

### Solución 2: Corregir permisos IAM
Actualizar el template.yaml para incluir permisos de lectura:
```yaml
TransferApiFunction:
  Properties:
    Policies:
      - DynamoDBCrudPolicy:  # Ya incluye GetItem
          TableName: !Ref BankingTable
      # Agregar explícitamente si es necesario:
      - DynamoDBReadPolicy:
          TableName: !Ref BankingTable
```

### Solución 3: Implementar control de concurrencia optimista
```typescript
// Usar versionado en los registros
UpdateExpression: 'SET Balance = Balance - :amount, HashKey = :hash, Version = Version + :inc',
ConditionExpression: 'Version = :currentVersion AND Balance >= :amount',
ExpressionAttributeValues: {
    ':amount': amount,
    ':hash': newSourceHash,
    ':inc': 1,
    ':currentVersion': sourceAccount.Item.Version
}
```

### Solución 4: Procesamiento secuencial para mismas cuentas
Implementar un sistema de colas o locks por cuenta para evitar transferencias concurrentes en las mismas cuentas.

La causa raíz es la **falta de atomicidad en las operaciones de transferencia combinada con condiciones de carrera**, lo que permite que el dinero se debite sin garantizar que se acredite correctamente, resultando en pérdida de fondos.