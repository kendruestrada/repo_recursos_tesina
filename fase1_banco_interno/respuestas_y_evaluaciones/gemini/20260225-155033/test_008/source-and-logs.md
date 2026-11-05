## [Titulo]: Pérdida de fondos por transferencias no transaccionales y throttling
### Resumen: Las transferencias descuentan el balance de la cuenta origen pero fallan al actualizar la cuenta destino debido a límites de rendimiento en DynamoDB, perdiendo el dinero.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir: Ejecutar múltiples transferencias de fondos de manera concurrente para forzar el límite de capacidad de escritura (WCU) de la tabla en DynamoDB. Esto sucede rápidamente ya que la función `generateKeyHash()` genera y actualiza un string de 40KB en cada operación.
- Esperado vs. Actual: Se espera que una transferencia sea una operación atómica (todo o nada). Actualmente, el sistema utiliza dos llamadas `UpdateCommand` independientes. Si el descuento a la cuenta origen es exitoso pero la suma a la cuenta destino falla (lanzando una excepción y abortando), el descuento no se revierte y los fondos desaparecen del sistema.
- Ubicacion del error: `src/transfer-api/app.ts` (funcion `processTransfer`) y `src/transfer-processor/app.ts` (funcion `handler`).
- Logs relevantes: `ERROR Transfer [ID] failed: ThrottlingException: Throughput exceeds the current capacity of your table or index... reason: 'TableWriteKeyRangeThroughputExceeded'`
### Propuesta de Solucion
Reemplazar los dos llamados independientes de `UpdateCommand` por una única transacción utilizando `TransactWriteItems` de DynamoDB, garantizando que el dinero solo se descuente si la suma también tiene éxito. Además, optimizar la generación de `HashKey` para no exceder innecesariamente el consumo de capacidad de escritura de la base de datos escribiendo ~40KB en cada transacción.

# Token Usage

Total Tokens: 183192
Prompt Tokens: 180296
Input Tokens (non-cached): 160064
Response Tokens: 555
Cached Tokens: 20232
Thoughts Tokens: 2341

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.320128
Cached Cost (USD):  $0.004046
Output Cost (USD):  $0.006660
Thoughts Cost (USD):$0.028092
Total Cost (USD):   $0.358926


# Execution time in seconds:

49
