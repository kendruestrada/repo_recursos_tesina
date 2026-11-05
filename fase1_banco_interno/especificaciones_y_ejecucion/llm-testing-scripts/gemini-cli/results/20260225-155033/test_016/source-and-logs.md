## Interbloqueo (Deadlock) y Fuga de Recursos en Transferencias Concurrentes
### Resumen: Un interbloqueo (deadlock) entre transacciones concurrentes en direcciones opuestas ocasiona un bucle infinito en la reserva de cuentas, agotando el tiempo de ejecución (timeout) de Lambda e impidiendo la liberación de los bloqueos.
### Severidad: Critical
### Analisis de causa raiz
- **Pasos para reproducir**:
  1. Iniciar una transacción T1 desde la cuenta A hacia la cuenta B.
  2. Simultáneamente, iniciar una transacción T2 desde la cuenta B hacia la cuenta A.
  3. T1 reserva/bloquea con éxito la cuenta A y T2 bloquea la cuenta B.
  4. Ambas transacciones llaman a `verify_settlement_window`, lo cual toma aproximadamente 15 segundos en responder.
  5. Una vez terminada la espera, T1 intenta bloquear la cuenta B (retenida por T2) y T2 intenta bloquear la cuenta A (retenida por T1).
- **Esperado vs. Actual**:
  - **Esperado**: El sistema procesa transacciones concurrentes evitando condiciones de carrera, o en su defecto, falla de manera controlada y garantiza que los bloqueos sobre las cuentas siempre se liberen.
  - **Actual**: Ocurre un interbloqueo (deadlock). La función de reserva intenta adquirir el bloqueo mediante un bucle infinito que nunca se rompe. Esto provoca que el entorno de ejecución de AWS Lambda exceda su tiempo máximo (timeout de 60 segundos) y sea terminado abruptamente. Como resultado, la ejecución no alcanza los bloques de control de errores para liberar las cuentas, dejándolas bloqueadas persistente y erróneamente en DynamoDB, dado que su funcionalidad de borrado por TTL ocurre de forma diferida.
- **Ubicacion del error**:
  - `src/transfer_funds.py` (función `handler`): Ausencia de ordenamiento jerárquico al adquirir recursos y retención de bloqueos durante llamadas de red externas (`verify_settlement_window`).
  - `src/resource_registry.py` (función `reserve_resource`): Uso de un bucle `while True` para el bloqueo condicional sin un tiempo máximo de espera interno y sin comprobación de la validez real del TTL de la tabla.
- **Logs relevantes**:
  - Se visualizan transacciones opuestas iniciadas simultáneamente:
    `TXN: 70199d48... | SRC: A | DST: B | STATE: START` (18:55:15.341)
    `TXN: 0b1f5693... | SRC: B | DST: A | STATE: START` (18:55:15.141)
  - Seguidas por el bloqueo en la fase 2 intentando reservar el recurso ocupado:
    `TXN: 0b1f5693... | RES: A | PH: 2 | STATE: ATTEMPT` (18:55:30.364)
    `TXN: 70199d48... | RES: B | PH: 2 | STATE: ATTEMPT` (18:55:30.674)
  - Posteriormente, los procesos terminan por timeout sin logs de conclusión (`STATE: FINISH` o `ERROR`):
    `Duration: 60000.00 ms ... Status: timeout` (18:56:14.507)

### Propuesta de Solucion
1. **Ordenar la Adquisición de Recursos**: Implementar un ordenamiento alfabético de las cuentas (ej. siempre bloquear la cuenta menor primero y la mayor después) dentro de `transfer_funds.py` para prevenir la dependencia circular y por ende el deadlock.
2. **Reubicar la Lógica de Red**: Adelantar la ejecución de `verify_settlement_window` antes de bloquear cualquier cuenta, o minimizar el tiempo que los recursos permanecen reservados inútilmente en espera de una entrada/salida de red.
3. **Limitar Reintentos de Bloqueo**: Modificar la función `reserve_resource` en `resource_registry.py` reemplazando el `while True` por un mecanismo de reintento con tiempo límite (timeout interno) que lance una excepción controlada, permitiendo rechazar la transferencia pero liberar el recurso ya retenido.
4. **Validación Segura de TTL**: Actualizar la condición `attribute_not_exists` en DynamoDB para permitir el sobreescrito lógico si el ítem existe pero su campo `ttl` ya ha expirado, mitigando las fallas cuando una Lambda muere repentinamente y DynamoDB aún no elimina el registro obsoleto en background.

# Token Usage

Total Tokens: 62834
Prompt Tokens: 58301
Input Tokens (non-cached): 42081
Response Tokens: 1151
Cached Tokens: 16220
Thoughts Tokens: 3382

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.084162
Cached Cost (USD):  $0.003244
Output Cost (USD):  $0.013812
Thoughts Cost (USD):$0.040584
Total Cost (USD):   $0.141802


# Execution time in seconds:

71
