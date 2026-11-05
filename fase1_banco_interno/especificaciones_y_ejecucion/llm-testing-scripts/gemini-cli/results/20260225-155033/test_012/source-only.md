## [Condición de Carrera y Caché Obsoleto]: Sobrescritura incorrecta de stock por uso de caché global y falta de atomicidad

### Resumen: La función Lambda retiene estado en una variable global entre ejecuciones y sobrescribe el inventario sin atomicidad, provocando lecturas de datos obsoletos y posibles ventas sin stock real.

### Severidad: Critical

### Analisis de causa raiz
- Pasos para reproducir
  1. Ejecutar una petición a la función Lambda para reducir el stock de un SKU. El stock de la base de datos se registra en el diccionario global `internal_cache`.
  2. Ejecutar inmediatamente peticiones adicionales en el mismo entorno de ejecución (warm start) intentando comprar más unidades del mismo SKU.
- Esperado vs. Actual
  - Esperado: Cada transacción debe validarse contra el stock actualizado y la reducción de inventario no debe afectar transacciones concurrentes, rechazando operaciones si no hay fondos o stock suficiente.
  - Actual: Las llamadas subsecuentes utilizan el valor inmutable guardado en `internal_cache` debido a la persistencia del estado global. Esto ocasiona que la validación inicial del stock sea falsa y se sobrescriba el estado de DynamoDB usando `put_item`, borrando las reducciones hechas por otras peticiones o generando stock negativo.
- Ubicacion del error (file/function)
  - Fichero: `inventory_handler/app.py`
  - Función: `lambda_handler` (almacenamiento en `internal_cache` y escritura insegura con `table.put_item`)
- Logs relevantes
  - "Estado DB antes: [stock_actualizado_pero_ignorado]"
  - "Visto en Cache: [stock_obsoleto_de_ejecucion_previa]"

### Propuesta de Solucion
- Eliminar el uso de la variable global `internal_cache` para validaciones críticas de inventario, dado que el estado en memoria de Lambda no es consistente entre invocaciones concurrentes.
- Modificar el método de acceso a la base de datos: sustituir la lectura previa y el subsecuente `table.put_item` por una única operación transaccional utilizando `table.update_item`.
- Implementar expresiones de actualización atómica en DynamoDB (`SET stock = stock - :quantity`) en conjunto con bloqueos condicionales (`ConditionExpression="stock >= :quantity"`). Esto asegura que la base de datos misma prevenga actualizaciones cuando el stock real es insuficiente, evitando cualquier condición de carrera o sobreventa.
- Capturar la excepción generada cuando la condición falla (por ejemplo, `ConditionalCheckFailedException`) para devolver correctamente el código HTTP 400 por falta de stock.

# Token Usage

Total Tokens: 13525
Prompt Tokens: 10819
Input Tokens (non-cached): 2763
Response Tokens: 587
Cached Tokens: 8056
Thoughts Tokens: 2119

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.005526
Cached Cost (USD):  $0.001611
Output Cost (USD):  $0.007044
Thoughts Cost (USD):$0.025428
Total Cost (USD):   $0.039609


# Execution time in seconds:

47
