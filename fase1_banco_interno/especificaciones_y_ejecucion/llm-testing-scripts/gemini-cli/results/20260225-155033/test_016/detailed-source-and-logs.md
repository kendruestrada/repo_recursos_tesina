## [Titulo]: Interbloqueo (Deadlock) y agotamiento de tiempo en transferencias concurrentes
### Resumen: Las transferencias cruzadas simultáneas provocan un interbloqueo al reservar recursos sin un orden definido ni límite de tiempo, causando un bloqueo infinito y aborto por timeout.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir:
  1. Iniciar una transacción Tx1 para transferir desde la cuenta A hacia la cuenta B.
  2. Simultáneamente, iniciar una transacción Tx2 para transferir desde la cuenta B hacia la cuenta A.
  3. Tx1 reserva la cuenta A de forma exitosa. Al mismo tiempo, Tx2 reserva la cuenta B exitosamente.
  4. Tx1 intenta reservar la cuenta B, la cual se encuentra retenida por Tx2, ingresando al ciclo de espera.
  5. Tx2 intenta reservar la cuenta A, la cual se encuentra retenida por Tx1, ingresando también al ciclo de espera.
  6. Ambos procesos quedan atrapados bloqueándose mutuamente hasta que el entorno finaliza forzosamente la ejecución al superar los 60 segundos de límite (timeout).
- Esperado vs. Actual:
  - Esperado: El sistema debería asegurar una adquisición determinista en la contención de recursos para prevenir interbloqueos y contar con un límite máximo de espera local. Si falla la reserva, el sistema debe liberar los registros previos de manera estructurada e informar al usuario.
  - Actual: El método de adquisición usa un bucle "while True" que reintenta infinitamente la operación de reserva en la base de datos sin un tope de tiempo. Esto desencadena un interbloqueo sin punto de salida que fuerza la interrupción del proceso por límite de ejecución, lo que a su vez previene la activación de las rutinas de liberación, dejando los registros de reserva estancados indefinidamente.
- Ubicacion del error (file/function):
  - src/resource_registry.py en la funcion reserve_resource (carencia de control de expiración o límite de reintentos en el bucle infinito).
  - src/transfer_funds.py en la funcion handler (adquisición secuencial de cuentas de origen y destino sujeta al orden de entrada del usuario, permitiendo interbloqueos circulares).
- Logs relevantes:
  - TXN: 7dbe18fe-8d12-4607-8b0a-929511fa64a5 | SRC: A | DST: B | STATE: START
  - TXN: 334cad94-82de-4a71-a8a2-baa62ad9d7d7 | SRC: B | DST: A | STATE: START
  - TXN: 7dbe18fe-8d12-4607-8b0a-929511fa64a5 | RES: A | PH: 1 | STATE: RESERVED
  - TXN: 334cad94-82de-4a71-a8a2-baa62ad9d7d7 | RES: B | PH: 1 | STATE: RESERVED
  - TXN: 7dbe18fe-8d12-4607-8b0a-929511fa64a5 | RES: B | PH: 2 | STATE: ATTEMPT
  - TXN: 334cad94-82de-4a71-a8a2-baa62ad9d7d7 | RES: A | PH: 2 | STATE: ATTEMPT
  - REPORT RequestId: 8f57952f-b602-4d00-8032-6e8c4d0e7924 Duration: 60000.00 ms Billed Duration: 60000 ms Memory Size: 256 MB Max Memory Used: 90 MB Status: timeout
### Propuesta de Solucion
1. Adquisicion ordenada de recursos: Modificar la funcion handler para ordenar lexicográficamente las cuentas origen y destino antes de requerir su reserva. Al obligar a las transacciones a adquirir el bloqueo siempre de la cuenta con menor valor léxico primero, se previenen los interbloqueos.
2. Limite de espera (Timeout Local): Modificar la estructura cíclica en la funcion reserve_resource de resource_registry.py para verificar el tiempo transcurrido, lanzando una excepción controlada si la adquisición del registro supera un umbral de seguridad estipulado (por ejemplo, 10 segundos).
3. Asegurar la consistencia del estado: Emplear mecanismos de control de errores (como bloque finally) en transfer_funds.py para asegurar incondicionalmente la ejecución de release_resource sobre aquellos identificadores exitosamente obtenidos en caso de cualquier falla durante la fase transaccional.

# Token Usage

Total Tokens: 64034
Prompt Tokens: 58204
Input Tokens (non-cached): 41983
Response Tokens: 1163
Cached Tokens: 16221
Thoughts Tokens: 4667

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.083966
Cached Cost (USD):  $0.003244
Output Cost (USD):  $0.013956
Thoughts Cost (USD):$0.056004
Total Cost (USD):   $0.157170


# Execution time in seconds:

82
