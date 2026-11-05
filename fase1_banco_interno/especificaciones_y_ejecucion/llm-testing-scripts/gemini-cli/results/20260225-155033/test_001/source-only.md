## Validación silenciosa de dirección causa fallo en el procesamiento de compra
### Resumen: La función validate-address oculta los errores del servicio externo devolviendo un código 200 con la dirección nula, lo que engaña al frontend y causa que la función process-purchase rechace la transacción con un error 400.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir:
  1. El usuario completa y envía el formulario en el frontend.
  2. El servicio externo consultado por `validate-address` (a través de `VALIDATION_SERVICE_URL`) falla o devuelve un código distinto a 200.
  3. `validate-address` captura el error pero responde al frontend con un código HTTP 200 y el campo `address` establecido como `null`.
  4. El frontend asume que la sincronización fue exitosa, habilita el botón de compra y guarda el objeto de datos con la dirección nula.
  5. El usuario hace clic en "Complete Purchase", enviando los datos a `process-purchase`.
  6. `process-purchase` detecta que `address` es nulo, devuelve un error HTTP 400 y el frontend se queda bloqueado mostrando "Processing..." indefinidamente por no manejar respuestas de error.
- Esperado vs. Actual:
  - Esperado: Si la validación de la dirección falla, `validate-address` debe retornar un código de error (ej. 400 o 502), para que el frontend informe al usuario del problema y no le permita continuar al siguiente paso de la compra.
  - Actual: `validate-address` retorna un estado 200 (exitoso) mutilando los datos (`address: null`). El flujo avanza con datos inválidos provocando un fallo silencioso en el siguiente paso de la compra.
- Ubicacion del error (file/function):
  - `src/validate-address/index.js` / función `handler` (manejo incorrecto del código HTTP ante un error del auditor).
  - `frontend/index.html` / listeners de `submit` y `click` (falta de manejo para status distintos de 200).
- Logs relevantes:
  - "External provider error: [status_code] - Invalid address format"
  - "Sync status: 200"
  - "Purchase rejected: shipping address is missing or null"

### Propuesta de Solucion
1. Modificar `src/validate-address/index.js` para que, cuando `audit.status !== 200`, devuelva un código HTTP acorde al fallo (por ejemplo 400 o 502) e informe en el cuerpo de la respuesta que la dirección es inválida, en lugar de forzar un estado 200 con `address: null`.
2. Actualizar `frontend/index.html` para validar correctamente los estados de error de la API (cuando `res.status !== 200`) en ambos llamados a `fetch`, y mostrar el mensaje de error correspondiente en el elemento con id `o`, en lugar de quedarse congelado en el estado "Processing..." y evitar habilitar el botón de compra si hay fallos.

# Token Usage

Total Tokens: 13910
Prompt Tokens: 11608
Input Tokens (non-cached): 11608
Response Tokens: 704
Cached Tokens: 0
Thoughts Tokens: 1598

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.023216
Cached Cost (USD):  $0.000000
Output Cost (USD):  $0.008448
Thoughts Cost (USD):$0.019176
Total Cost (USD):   $0.050840


# Execution time in seconds:

46
