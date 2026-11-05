## [Titulo]: Fuga de memoria en caché global durante la generación de reportes
### Resumen: La aplicación agota la memoria configurada de la Lambda debido a un crecimiento persistente al acumular datos de cada ejecución en una variable global.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir:
  1. Realizar múltiples peticiones continuas al endpoint para solicitar la generación de reportes PDF.
  2. Monitorear el incremento gradual de la memoria en uso a través de los reportes en CloudWatch.
  3. Repetir el proceso hasta que la Lambda rebase su límite de capacidad (128 MB) y se interrumpa el servicio.
- Esperado vs. Actual:
  - Esperado: El consumo de memoria debe mantenerse acotado y estable; la memoria transitoria utilizada para generar un reporte debe ser recolectada al terminar la ejecución, permitiendo que la aplicación se mantenga rápida independiente de la cantidad de peticiones.
  - Actual: Debido a la reutilización del entorno de ejecución de la Lambda, el estado de las variables globales perdura. En cada invocación, la función añade a la lista global un documento de plantilla y una lista numérica cuyo tamaño aumenta secuencialmente. Esto origina lentitud por sobrecarga y posteriormente caídas del servicio por falta de memoria.
  - Ejemplo de ejecución: En la primera llamada (`count` = 1) se reserva en memoria una lista de 100,000 elementos. En la llamada número 50 (`count` = 50), la función intenta agregar una lista de 5,000,000 elementos al arreglo global que ya contiene las llamadas previas, ocasionando un cuelgue inminente.
- Ubicacion del error (file/function):
  - Archivo: `lambda/report.py`
  - Función: `template()` y declaración de variables globales (`TEMPLATE_CACHE = []` y `count = 0`).
- Logs relevantes:
  - `REPORT RequestId: 57f78843-e2ba-43ee-b596-2abd2d2ad9f4 Duration: 6090.59 ms Billed Duration: 6091 ms Memory Size: 128 MB Max Memory Used: 127 MB Status: error Error Type: Runtime.OutOfMemory`
### Propuesta de Solucion
1. Remover el almacenamiento innecesario de objetos generados y listas pesadas en la variable global `TEMPLATE_CACHE`, particularmente borrando la instrucción donde se anexa la información a esta lista compartida.
2. Eliminar la generación secuencial masiva de registros (`my_list`) que provocan directamente el desbordamiento.
3. En caso de requerir un sistema de caché real para las plantillas, se debe implementar una estructura que limite su capacidad (por ejemplo, vaciar la lista pasada cierta cantidad o usar algoritmos como LRU), o bien integrar servicios de retención externa como ElastiCache o DynamoDB.
4. Evaluar si la capacidad de memoria base de 128 MB definida en `lib/test_009-stack.ts` es la óptima para las operaciones de la biblioteca FPDF una vez corregida la fuga de memoria.

# Token Usage

Total Tokens: 49715
Prompt Tokens: 46028
Input Tokens (non-cached): 25736
Response Tokens: 769
Cached Tokens: 20292
Thoughts Tokens: 2918

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.051472
Cached Cost (USD):  $0.004058
Output Cost (USD):  $0.009228
Thoughts Cost (USD):$0.035016
Total Cost (USD):   $0.099774


# Execution time in seconds:

72
