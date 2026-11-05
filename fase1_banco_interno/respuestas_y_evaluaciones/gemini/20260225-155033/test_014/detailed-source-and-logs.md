## Registro duplicado de puntos y sobreescritura de datos en DynamoDB
### Resumen: La aplicación duplica los puntos otorgados debido a un evento procesado dos veces por reglas duplicadas, además de eliminar otros datos del usuario por un mal uso de DynamoDB.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir
  1. Se invoca el flujo de compra, el cual emite un único evento de tipo `PurchaseCompleted` hacia EventBridge.
  2. Debido a la existencia de dos reglas separadas que escuchan exactamente el mismo patrón de evento, la función lambda encargada de asignar los puntos se invoca dos veces.
  3. La lambda lee los puntos actuales del usuario y le suma los obtenidos. Al ejecutarse por duplicado, se otorgan el doble de puntos correspondientes.
  4. Al finalizar, guarda los datos usando `put_item`, lo que reemplaza todo el documento en base de datos.
- Esperado vs. Actual
  - Esperado: El evento se procesa una sola vez sumando la cantidad correcta de puntos, y la actualización en la base de datos conserva el resto de información del usuario en su registro.
  - Actual: El sistema procesa la misma compra dos veces seguidas. Adicionalmente, el método empleado para guardar los datos (`put_item`) reemplaza el ítem completo, borrando accidentalmente cualquier otro dato previo del usuario y siendo altamente vulnerable a inconsistencias de datos por condiciones de carrera.
- Ubicacion del error (file/function)
  - `template.yaml` (Reglas de EventBridge duplicadas: Recurso explícito `PurchaseRule` y el evento SAM `PurchaseEvent` bajo `UpdateLoyaltyPointsFunction`).
  - `src/update_points.py` (Función `handler`, uso inadecuado de `table.get_item` seguido de `table.put_item`).
- Logs relevantes
  En los logs de la función UpdateLoyaltyPointsFunction se observa claramente la doble ejecución para el mismo usuario con milisegundos de diferencia:
  `Processing points update for user user_test_14: +50`
  `Current points for user_test_14: 100`
  `Updated points for user_test_14: 150`
  (Milisegundos despues)
  `Processing points update for user user_test_14: +50`
  `Current points for user_test_14: 150`
  `Updated points for user_test_14: 200`
### Propuesta de Solucion
1. **Eliminar la duplicidad de EventBridge:** En el archivo `template.yaml`, borrar el recurso manual `PurchaseRule` y mantener únicamente la definición `PurchaseEvent` dentro de las propiedades (Events) de la función `UpdateLoyaltyPointsFunction`.
2. **Refactorizar la escritura en DynamoDB:** Modificar `update_points.py` para utilizar una sola operación atómica mediante `table.update_item` usando `UpdateExpression="ADD points :val"`. Esto elimina la necesidad de hacer un `get_item` previo, resuelve la vulnerabilidad de las condiciones de carrera concurrentes y evita borrar los demás atributos del usuario.
3. **Manejo de Idempotencia:** Implementar lógica para validar la unicidad de las transacciones (por ejemplo, validando un ID de transacción o el `id` propio del evento de EventBridge) antes de realizar la suma, mitigando así reintentos naturales de la red o envíos duplicados por parte de los clientes.

# Token Usage

Total Tokens: 2505664
Prompt Tokens: 2476628
Input Tokens (non-cached): 613028
Response Tokens: 1640
Cached Tokens: 1863600
Thoughts Tokens: 27396

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $1.226056
Cached Cost (USD):  $0.372720
Output Cost (USD):  $0.019680
Thoughts Cost (USD):$0.328752
Total Cost (USD):   $1.947208


# Execution time in seconds:

478
