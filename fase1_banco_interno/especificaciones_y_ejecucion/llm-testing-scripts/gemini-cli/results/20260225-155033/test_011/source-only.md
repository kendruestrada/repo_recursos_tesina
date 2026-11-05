## Error de variables locales no asignadas al procesar la orden
### Resumen: La función falla al intentar acceder a variables que no han sido inicializadas cuando los campos requeridos no están presentes en la petición.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir: Enviar una petición HTTP a la función `process_order` cuyo cuerpo (`body`) en formato JSON omita los campos `customer_email` o `amount` (por ejemplo: `{"order_id": "123"}`).
- Esperado vs. Actual: Se esperaría que la API valide la entrada y retorne un error HTTP 400 (Bad Request) indicando los campos faltantes, o que procese el mensaje con valores por defecto. Actualmente, la función colapsa y arroja una excepción en tiempo de ejecución (`UnboundLocalError`).
- Ubicacion del error: `process_order/app.py` en la función `lambda_handler`.
- Logs relevantes: Aunque no se proveyeron logs, en CloudWatch aparecerá una traza con el error: `UnboundLocalError: local variable 'customer_email' referenced before assignment` (o sobre la variable `amount`).
### Propuesta de Solucion
Se recomienda validar la existencia de los campos obligatorios al principio de la función y retornar una respuesta HTTP 400 en caso de que falten. Si los campos son opcionales, se deben inicializar las variables con valores por defecto (ej. `None`) antes de las condicionales, o utilizar el método `.get()` de los diccionarios, de esta forma: `customer_email = body.get("customer_email")` y `amount = body.get("amount")`.

# Token Usage

Total Tokens: 13071
Prompt Tokens: 10855
Input Tokens (non-cached): 2799
Response Tokens: 373
Cached Tokens: 8056
Thoughts Tokens: 1843

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.005598
Cached Cost (USD):  $0.001611
Output Cost (USD):  $0.004476
Thoughts Cost (USD):$0.022116
Total Cost (USD):   $0.033801


# Execution time in seconds:

60
