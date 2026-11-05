## [Titulo]: Problema de stock negativo debido a validacion con estado global desactualizado
### Resumen: La funcion Lambda utiliza una variable global no actualizada en memoria como cache para validar el stock, lo que permite aprobar peticiones que sobrepasan el inventario real de la base de datos durante ejecuciones con warm start.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir
  1. Se envia una peticion inicial para el producto SKU-7821. La funcion obtiene el stock desde DynamoDB (por ejemplo, 5 unidades) y lo asigna al diccionario global "internal_cache".
  2. La funcion aprueba el descuento, resta la cantidad y actualiza el stock en la base de datos (por ejemplo, a 2 unidades). Sin embargo, el valor dentro de "internal_cache" no se actualiza ni se elimina.
  3. El contenedor de Lambda queda activo (warm start) y recibe una peticion posterior para descontar 5 unidades del mismo SKU.
  4. Al evaluar la disponibilidad, la condicion "if cached_val >= quantity:" utiliza el valor estancado en cache (5 >= 5), resultando verdadero.
  5. La funcion resta la cantidad solicitada (5) del nuevo stock leido en DynamoDB (2), generando una variable "new_stock" con valor de -3, la cual es guardada en la base de datos.
- Esperado vs. Actual
  - Esperado: El sistema debe contrastar la cantidad requerida estrictamente contra el stock real de la base de datos de manera transaccional. Si el inventario es menor a la peticion, se debe retornar el error 400 "Low stock" y detener el flujo.
  - Actual: El sistema confia en un estado de memoria global contaminado por ejecuciones previas, permitiendo que la condicion de disponibilidad se cumpla a pesar de que la cantidad solicitada sea mayor al stock real de DynamoDB, resultando en inventarios negativos.
- Ubicacion del error (file/function)
  - Archivo: @inventory_handler/app.py
  - Funcion: lambda_handler
- Logs relevantes
  - 2026-02-25 13:00:25.724: "Estado DB antes: 2"
  - 2026-02-25 13:00:25.724: "Visto en Cache: 5"
  - 2026-02-25 13:00:26.242: "Estado DB despues: -3"
### Propuesta de Solucion
1. Eliminar de forma permanente el uso de la variable global "internal_cache" para realizar la validacion del inventario disponible. La logica de validacion no debe depender del estado en memoria del contenedor.
2. Reemplazar el patron actual de lectura y escritura ("get_item" seguido de procesamiento y "put_item") por la operacion atomica "update_item" de la libreria Boto3 para DynamoDB.
3. Implementar un "ConditionExpression" (ej. "stock >= :qty") en la llamada a "update_item" de la base de datos. De esta forma la operacion de resta de inventario fallara automaticamente y a nivel de base de datos si ocurre un problema de concurrencia o si el stock real es menor a la cantidad solicitada.
4. Remover la funcion "time.sleep(0.5)", la cual exacerba enormemente las condiciones de carrera en un entorno de multiples peticiones concurrentes.

# Token Usage

Total Tokens: 103193
Prompt Tokens: 98168
Input Tokens (non-cached): 49321
Response Tokens: 942
Cached Tokens: 48847
Thoughts Tokens: 4083

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.098642
Cached Cost (USD):  $0.009769
Output Cost (USD):  $0.011304
Thoughts Cost (USD):$0.048996
Total Cost (USD):   $0.168711


# Execution time in seconds:

80
