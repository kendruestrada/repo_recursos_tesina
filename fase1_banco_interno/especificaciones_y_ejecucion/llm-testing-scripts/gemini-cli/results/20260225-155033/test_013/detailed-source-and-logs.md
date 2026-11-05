## Agotamiento del pool de conexiones causante de tiempos de espera (Timeout)
### Resumen: Las conexiones no se liberan de vuelta al pool tras ejecuciones exitosas, lo que agota el semáforo y bloquea peticiones subsecuentes causando un timeout.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir: Enviar peticiones válidas consecutivas al endpoint expuesto. Las primeras 5 peticiones (definidas por `maxconn=5`) se procesarán de manera casi instantánea, pero la 6ta petición se quedará bloqueada en un bucle de espera, lo que terminará provocando un error por timeout tras cumplirse el límite de tiempo.
- Esperado vs. Actual: Se espera que, tras obtener una conexión (`connection_pool.getconn()`), esta se devuelva siempre al pool usando `connection_pool.putconn(conn)`. Actualmente, esta liberación ocurre únicamente si la ejecución falla entrando al bloque `except`. En una ejecución exitosa, la conexión no se devuelve, perdiendo un cupo del semáforo hasta llegar a 0 e impidiendo resolver llamadas posteriores.
- Ubicacion del error: `app/app.py` / función `lambda_handler`
- Logs relevantes:
  `REPORT RequestId: 74715b57-65ea-4e86-a73a-2ca31e4b7e65 Duration: 30000.00 ms Billed Duration: 30000 ms Memory Size: 256 MB Max Memory Used: 40 MB Status: timeout`
### Propuesta de Solucion
Se recomienda incluir un bloque `finally` que contenga la función `connection_pool.putconn(conn)`. Al agrupar esta instrucción dentro de la estructura `try-except-finally`, se garantiza que la conexión a la base de datos siempre sea liberada y puesta a disposición en el pool para la siguiente invocación, tanto en resoluciones exitosas como en casos de fallos en la función `lambda_handler`.

# Token Usage

Total Tokens: 51485
Prompt Tokens: 48617
Input Tokens (non-cached): 32409
Response Tokens: 506
Cached Tokens: 16208
Thoughts Tokens: 2362

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.064818
Cached Cost (USD):  $0.003242
Output Cost (USD):  $0.006072
Thoughts Cost (USD):$0.028344
Total Cost (USD):   $0.102476


# Execution time in seconds:

54
