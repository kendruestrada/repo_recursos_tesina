## [Titulo]: Inconsistencia de datos por falta de atomicidad y condiciones de carrera en las transferencias
### Resumen: La operación de transferencia realiza actualizaciones independientes en las cuentas de origen y destino sin utilizar transacciones, permitiendo saldos negativos y pérdida irrecuperable de fondos ante fallos concurrentes.
### Severidad: Critical
### Analisis de causa raiz
- **Pasos para reproducir**: 
  1. Para provocar pérdida de fondos: Provocar una excepción (como un fallo de red o tiempo de espera agotado) durante la ejecución del segundo `UpdateCommand` (cuenta destino), después de que el primer `UpdateCommand` (cuenta origen) haya finalizado exitosamente.
  2. Para provocar saldos negativos: Ejecutar simultáneamente dos transferencias desde una misma cuenta origen cuyo monto individual sea válido, pero sumados superen el balance real. Ambas validaciones en memoria pasarán y deducirán fondos, llevando el balance por debajo de cero.
- **Esperado vs. Actual**: 
  - Esperado: El proceso de transferencia debe ser una operación "Todo o Nada" (atómica). Si falla el abono al destino, no se debe realizar el descuento en el origen. La comprobación de fondos debe realizarse de forma segura en la base de datos al momento exacto de descontar.
  - Actual: El código efectúa el descuento en el origen y luego el abono en el destino de manera secuencial y aislada. No se valida a nivel de base de datos que el balance actual sea suficiente durante la propia actualización (ausencia de ConditionExpression).
- **Ubicacion del error (file/function)**: 
  - `src/transfer-api/app.ts` en la función `processTransfer`
  - `src/transfer-processor/app.ts` en la función `handler`
- **Logs relevantes**: Al suceder un fallo a mitad del proceso, se registrará por consola `Transfer [id] failed: [error]` y en la tabla de auditoría se guardará el intento con `Status: 'failed'`, a pesar de que la base de datos ya modificó de manera permanente y sin posibilidad de rollback el balance de la cuenta origen.

### Propuesta de Solucion
Sustituir las llamadas secuenciales de `UpdateCommand` por una única operación transaccional empleando `TransactWriteCommand` (TransactWriteItems de DynamoDB) que contenga la actualización de ambas cuentas en el mismo llamado. Adicionalmente, incluir un `ConditionExpression: 'Balance >= :amount'` en la operación de actualización de la cuenta de origen para garantizar atómicamente que existen los fondos requeridos al instante de efectuar la deducción, mitigando por completo las condiciones de carrera.

# Token Usage

Total Tokens: 23877
Prompt Tokens: 14672
Input Tokens (non-cached): 6581
Response Tokens: 581
Cached Tokens: 8091
Thoughts Tokens: 8624

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.013162
Cached Cost (USD):  $0.001618
Output Cost (USD):  $0.006972
Thoughts Cost (USD):$0.103488
Total Cost (USD):   $0.125240


# Execution time in seconds:

114
