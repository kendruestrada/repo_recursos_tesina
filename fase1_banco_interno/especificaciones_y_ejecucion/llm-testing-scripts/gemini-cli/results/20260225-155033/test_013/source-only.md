## Fuga de conexiones en pool por omisión de liberación en flujo exitoso
### Resumen: La función lambda agota las conexiones del pool al no devolverlas durante las ejecuciones que terminan correctamente, provocando un bloqueo total del proceso después de cinco peticiones.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir: 
  1. Enviar cinco peticiones válidas y exitosas a la función lambda utilizando el mismo contenedor caliente de ejecución. 
  2. Enviar una sexta petición. 
  3. La sexta petición se quedará bloqueada indefinidamente, ya que el pool alcanzó su límite de 5 conexiones y la ejecución se suspenderá hasta que la función lambda alcance su tiempo límite (timeout).
- Esperado vs. Actual: 
  Esperado: Toda conexión obtenida del pool (connection_pool.getconn()) debe ser devuelta una vez que finaliza el procesamiento de la petición, sin importar el resultado. 
  Actual: La función libera la conexión (connection_pool.putconn(conn)) exclusivamente dentro del bloque "except". Si el flujo es exitoso y retorna código 200, la conexión nunca es liberada, causando una fuga de recursos.
- Ubicacion del error: app/app.py / función lambda_handler
- Logs relevantes: No existen trazas de error en los logs iniciales de ejecución. Al presentarse la falla, el único indicio observable será un "Task timed out" emitido por la infraestructura al bloquearse de forma permanente el hilo en la adquisición del semáforo.
### Propuesta de Solucion
Refactorizar el manejo de excepciones en la función lambda_handler utilizando una estructura "try-except-finally". La liberación de la conexión mediante el método "connection_pool.putconn(conn)" debe trasladarse al bloque "finally", retirándose del bloque "except". Esto asegurará de manera determinista que la conexión retorne al pool en todos los escenarios posibles (éxito o fallo de la transacción).

# Token Usage

Total Tokens: 13262
Prompt Tokens: 10839
Input Tokens (non-cached): 2783
Response Tokens: 433
Cached Tokens: 8056
Thoughts Tokens: 1990

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.005566
Cached Cost (USD):  $0.001611
Output Cost (USD):  $0.005196
Thoughts Cost (USD):$0.023880
Total Cost (USD):   $0.036253


# Execution time in seconds:

40
