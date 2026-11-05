## [Titulo]: Lentitud en búsqueda de productos por límite de 1MB en DynamoDB provocado por sobre-extracción de datos
### Resumen: La extracción innecesaria del atributo pesado 'data' fuerza múltiples viajes de red hacia DynamoDB por petición debido al límite de lectura de 1MB, impactando los tiempos de respuesta.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir: Realizar una petición GET al endpoint de búsqueda para una categoría con registros pesados (ej. `/search?category=electronics&limit=20`).
- Esperado vs. Actual: Se espera que la búsqueda devuelva los productos en pocos milisegundos de forma constante (como sucede con la categoría `books` que demora menos de 50ms). Actualmente, las peticiones para la categoría `electronics` tardan en promedio más de 500ms y registran picos de latencia de hasta 1100ms.
- Ubicacion del error (file/function): `product_service/app.py` en la función `lambda_handler`, específicamente en la configuración de `query_kwargs` y el bucle iterativo `while True` que ejecuta las consultas.
- Logs relevantes: En el LogGroup `/aws/lambda/SearchProductsFunction` se aprecian registros `REPORT` con tiempos excesivos, por ejemplo: `REPORT RequestId: df26865d-a517... Duration: 1095.98 ms` o `REPORT RequestId: b9347037-8ea0... Duration: 539.05 ms`.

DynamoDB posee un límite de tamaño de carga útil de 1MB por resultado de consulta. Debido a que el atributo `data` de cada producto en ciertas categorías (`electronics`) es muy pesado, una única llamada a `table.query` no alcanza a devolver los elementos solicitados (`fetch_limit`). Esto fuerza al código a entrar en repetidas iteraciones usando `LastEvaluatedKey` dentro del bucle `while True` para alcanzar el tamaño límite deseado de la página, consumiendo recursos de red, tiempo y memoria en cada iteración. Paradójicamente, el pesado atributo `data` luego es sobrescrito con el valor `(payload hidden)`, por lo que no es necesario para construir la respuesta final de la API.

### Propuesta de Solucion
1. Agregar el parámetro `ProjectionExpression` a la definición de `query_kwargs` para recuperar estrictamente aquellos atributos necesarios en la respuesta de la API (por ejemplo: `category_id`, `product_id`, `price`, etc.) e instruir explícitamente a DynamoDB que ignore el atributo `data`. De este modo, los ítems se procesarán más rápido y cabrán sin problema en una sola lectura antes de cruzar la barrera de 1MB, eliminando el problema de paginación exhaustiva.
2. Como hallazgo concurrente al análisis de la función `lambda_handler`, se identificó que el parámetro de entrada `page` está siendo analizado pero jamás es utilizado para afectar la posición de lectura (offset), lo que significa que el listado de cualquier página superior a 1 devolverá erróneamente siempre el mismo bloque de elementos. Se sugiere refactorizar la lógica para recibir y pasar el `ExclusiveStartKey` devuelto al cliente y abandonar la dependencia de un simple número de página.

# Token Usage

Total Tokens: 671348
Prompt Tokens: 664006
Input Tokens (non-cached): 121066
Response Tokens: 1287
Cached Tokens: 542940
Thoughts Tokens: 6055

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.242132
Cached Cost (USD):  $0.108588
Output Cost (USD):  $0.015444
Thoughts Cost (USD):$0.072660
Total Cost (USD):   $0.438824


# Execution time in seconds:

193
