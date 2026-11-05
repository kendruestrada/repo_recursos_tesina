## Rendimiento degradado en busquedas por paginacion y limites de lectura en DynamoDB
### Resumen: Las busquedas para ciertas categorias son lentas porque los registros contienen atributos de gran tamaño que agotan el limite de 1MB por consulta de DynamoDB, forzando multiples peticiones de red secuenciales.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir: Realizar una solicitud a la API para listar productos utilizando `category=electronics` y `limit=20`.
- Esperado vs. Actual: Se espera que el listado retorne en pocos milisegundos de forma eficiente (como ocurre con la categoria "books" que promedia ~10ms). Actualmente, la busqueda toma alrededor de 1 segundo en responder para la categoria "electronics".
- Ubicacion del error (file/function): `product_service/app.py`, funcion `lambda_handler` (dentro del bucle `while True` que procesa `table.query`).
- Inconsistencias en el flujo de ejecucion: El codigo consulta a DynamoDB en un bucle `while True` hasta juntar `fetch_limit` (20 items). Sin embargo, al descargar el item completo, el atributo `data` aumenta considerablemente el peso del registro. Esto provoca que la base de datos alcance el limite estricto de 1MB por operacion `Query` devolviendo solo 1 o 2 items a la vez y un `LastEvaluatedKey`. En consecuencia, la aplicacion realiza numerosos viajes de red hacia DynamoDB hasta completar los 20 items. Ademas, se gasta capacidad de lectura de la tabla en el atributo `data` para luego ser ocultado en el codigo: `safe_item["data"] = "(payload hidden)"`.
- Ejemplo de ejecucion:
  - Entrada: Evento con `queryStringParameters: {"category": "electronics", "limit": "20"}`
  - Proceso interno: `table.query(Limit=20)` evalua hasta 1MB y retorna 2 elementos. En la siguiente iteracion del bucle, la nueva `query` con `Limit=18` retorna otros 2. Este proceso se repite 10 veces, retrasando en cada ciclo la ejecucion final.
  - Salida esperada: JSON con 20 items y el campo `"data": "(payload hidden)"`.
- Logs relevantes:
  - Tiempos elevados en logs generados por `SearchProductsFunction`: `REPORT RequestId: df26865d-a517... Duration: 1095.98 ms` (categoria `electronics`).
  - Diferencia de duracion comparada con ejecuciones ligeras: `REPORT RequestId: b3062bb7-27e8... Duration: 7.26 ms` (categoria `books`).

### Propuesta de Solucion
1. Modificar el diccionario `query_kwargs` en `app.py` para incluir una propiedad `ProjectionExpression` que obtenga unicamente los atributos requeridos por el negocio y excluya explicitamente de la consulta el pesado atributo `data`.
2. Al excluir los atributos voluminosos, la consulta podra obtener la maxima cantidad de items sin toparse repetidamente con el limite de 1MB de DynamoDB, permitiendo recuperar los 20 registros en una unica operacion a la base de datos y acelerando los tiempos de respuesta.
3. El bloque del codigo que limpia el campo de respuesta seguira siendo util al asignar manualmente `safe_item["data"] = "(payload hidden)"` para mantener el contrato original de la API de salida al cliente sin necesidad de transferir megabytes de datos innecesarios a la funcion Lambda.

# Token Usage

Total Tokens: 1094782
Prompt Tokens: 1087028
Input Tokens (non-cached): 302171
Response Tokens: 2204
Cached Tokens: 784857
Thoughts Tokens: 5550

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.604342
Cached Cost (USD):  $0.156971
Output Cost (USD):  $0.026448
Thoughts Cost (USD):$0.066600
Total Cost (USD):   $0.854361


# Execution time in seconds:

172
