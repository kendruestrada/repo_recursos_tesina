## [Titulo]: Interbloqueo (Deadlock) en reserva cruzada de cuentas concurrentes
### Resumen: La adquisicion de bloqueos de recursos sin un orden global predeterminado y el uso de un bucle de reintento infinito causan un interbloqueo durante transferencias cruzadas simultaneas.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir: Ejecutar dos transacciones concurrentemente. La Transaccion 1 intenta transferir fondos de la cuenta A hacia la cuenta B. Al mismo tiempo, la Transaccion 2 intenta transferir fondos de la cuenta B hacia la cuenta A.
- Esperado vs. Actual: Se esperaria que las transacciones se procesen secuencialmente o que una aborte de forma controlada. Actualmente, la Transaccion 1 bloquea la cuenta A y la Transaccion 2 bloquea la cuenta B. Luego, la Transaccion 1 intenta bloquear B (esperando a la Transaccion 2) y la Transaccion 2 intenta bloquear A (esperando a la Transaccion 1), generando un interbloqueo (deadlock) que detiene la ejecucion en un bucle infinito.
- Ubicacion del error (file/function): src/transfer_funds.py en la funcion `handler` (por el orden de reserva de bloqueos) y src/resource_registry.py en la funcion `reserve_resource` (por el bucle de espera infinito `while True`).
- Logs relevantes: Los registros mostrarian ambas transacciones deteniendose despues de imprimir `TXN: <id> | RES: <source> | PH: 1 | STATE: RESERVED`. Nunca se imprimiria el log correspondiente a `STATE: ATTEMPT` ni `STATE: FINISH`, y las funciones Lambda eventualmente fallarian por un error de tiempo de espera (Timeout) del entorno.
### Propuesta de Solucion
- Establecer un ordenamiento determinista (por ejemplo, ordenamiento lexico o alfabetico) para los identificadores de cuenta antes de bloquearlos. Indistintamente de quien sea el origen o el destino, el sistema siempre debe intentar bloquear primero la cuenta "menor" y luego la cuenta "mayor". Esto erradica la posibilidad de interbloqueos matematicamente.
- Modificar el bucle `while True` de la funcion `reserve_resource` para que posea un limite maximo de iteraciones o un tiempo maximo de espera (Timeout global). Si no se logra obtener el bloqueo dentro de este tiempo, se debe lanzar una excepcion controlada para que la transferencia aborte y libere los recursos previamente adquiridos.

# Token Usage

Total Tokens: 13460
Prompt Tokens: 11250
Input Tokens (non-cached): 3189
Response Tokens: 565
Cached Tokens: 8061
Thoughts Tokens: 1645

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.006378
Cached Cost (USD):  $0.001612
Output Cost (USD):  $0.006780
Thoughts Cost (USD):$0.019740
Total Cost (USD):   $0.034510


# Execution time in seconds:

41
