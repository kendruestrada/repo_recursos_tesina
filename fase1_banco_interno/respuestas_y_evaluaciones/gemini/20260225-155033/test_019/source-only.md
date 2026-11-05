## [Titulo]: Defecto en lógica de paginación y falta de validación de límites en DynamoDB
### Resumen: El parámetro de paginación es parseado pero completamente ignorado en la consulta, devolviendo siempre los mismos resultados, y el parámetro de límite carece de validación mínima permitiendo excepciones en la base de datos.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir:
  1. Para evidenciar el error de lógica de paginación: Realizar una solicitud `GET /search?category=electronics&page=2&limit=20`.
  2. Para evidenciar el error en tiempo de ejecución: Realizar una solicitud `GET /search?category=electronics&limit=0` o con un valor negativo.
- Esperado vs. Actual:
  - Esperado: Al solicitar `page=2`, el sistema debe desplazar el conjunto de resultados y omitir los primeros 20 elementos. Al enviar un `limit=0`, el sistema debe asignar un límite válido por defecto o devolver un error de validación al cliente (HTTP 400).
  - Actual: La API devuelve siempre la primera página de resultados sin importar el valor de `page` debido a que dicha variable no se usa para alterar el punto de inicio de la búsqueda o segmentar el resultado. Además, pasar `limit=0` propaga este valor hacia `boto3`, resultando en un HTTP 500 originado por la validación estricta de AWS DynamoDB.
- Ubicacion del error (file/function): `product_service/app.py` dentro de la función `lambda_handler`.
- Logs relevantes:
  - Error en caso de límite cero o negativo: `[ERROR] Error consultando DynamoDB: An error occurred (ValidationException) when calling the Query operation: Limit must be greater than 0`
### Propuesta de Solucion
1. **Corregir validación del límite**: Añadir una condición inmediatamente después de extraer el parámetro `limit` para garantizar que sea un valor funcional:
   ```python
   try:
       limit = int(query_params.get("limit", 20))
       if limit < 1:
           limit = 20
   except (ValueError, TypeError):
       limit = 20
   ```
2. **Corregir la lógica de paginación por desplazamiento (Offset)**: Utilizar la variable `page` para calcular la cantidad de registros a obtener y descartar los registros de las páginas anteriores antes de devolver el resultado:
   ```python
   skip_items = (page - 1) * limit
   fetch_limit = skip_items + limit
   
   # ... [Mismo código del ciclo while de DynamoDB] ...
   
   items = all_items[skip_items:fetch_limit]
   ```
3. **Alternativa arquitectónica**: Para un manejo eficiente en DynamoDB (evitando escaneos costosos), se recomienda sustituir el uso numérico de `page` por un sistema de paginación basado en cursores, en el cual el cliente envía directamente un token asociado al `LastEvaluatedKey`.

# Token Usage

Total Tokens: 34095
Prompt Tokens: 24772
Input Tokens (non-cached): 8633
Response Tokens: 706
Cached Tokens: 16139
Thoughts Tokens: 8617

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.017266
Cached Cost (USD):  $0.003228
Output Cost (USD):  $0.008472
Thoughts Cost (USD):$0.103404
Total Cost (USD):   $0.132370


# Execution time in seconds:

130
