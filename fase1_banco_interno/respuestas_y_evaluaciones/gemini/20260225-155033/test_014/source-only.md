## [Titulo]: Ejecución duplicada y condición de carrera en actualización de puntos
### Resumen: La función de actualización de puntos se ejecuta dos veces por cada evento debido a reglas de EventBridge duplicadas y presenta una condición de carrera al actualizar DynamoDB.
### Severidad: High
### Analisis de causa raiz
- Pasos para reproducir
  1. Invocar el endpoint de proceso de compras (`/purchase`) con los datos del usuario y los puntos obtenidos.
  2. El evento `PurchaseCompleted` es emitido hacia el bus de eventos.
  3. Revisar los logs de CloudWatch de `UpdateLoyaltyPointsFunction` y el registro correspondiente en la tabla de DynamoDB.
- Esperado vs. Actual
  - Esperado: El balance de puntos del usuario debe incrementarse exactamente una vez según el valor de `points_earned`.
  - Actual: La función se dispara dos veces por el mismo evento. Debido a una condición de carrera, a veces los puntos se duplican (sumando dos veces) y otras veces la segunda ejecución sobrescribe a la primera ignorando la suma concurrente, generando inconsistencias en los saldos.
- Ubicacion del error (file/function)
  - `template.yaml`: Declaración redundante de triggers de eventos. Existe un recurso explícito `PurchaseRule` y simultáneamente un evento implícito `PurchaseEvent` en `UpdateLoyaltyPointsFunction` que apuntan al mismo patrón de captura.
  - `src/update_points.py` (función `handler`): Patrón de lectura-modificación-escritura no atómico usando `get_item` seguido de `put_item` para actualizar los saldos en DynamoDB.
- Logs relevantes
  - Aunque no se proveen logs específicos, en un entorno de ejecución real se observarían registros duplicados de "Received event: ..." y "Processing points update for user..." en una misma franja de milisegundos para el mismo identificador de evento.

### Propuesta de Solucion
1. **Eliminar reglas duplicadas en EventBridge:** Modificar `template.yaml` para remover el recurso explícito `PurchaseRule` (y su respectivo `PurchaseRulePermission`), manteniendo únicamente la definición del evento `PurchaseEvent` dentro de las propiedades de la función `UpdateLoyaltyPointsFunction`.
2. **Utilizar operaciones atómicas en DynamoDB:** Modificar `src/update_points.py` para reemplazar el patrón de `get_item` seguido de `put_item` por un método `update_item` de DynamoDB con una expresión `ADD`. Esto previene la condición de carrera asegurando que la operación de suma se procese atómicamente en la base de datos sin depender de lecturas previas.

# Token Usage

Total Tokens: 30190
Prompt Tokens: 23334
Input Tokens (non-cached): 7210
Response Tokens: 609
Cached Tokens: 16124
Thoughts Tokens: 6247

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.014420
Cached Cost (USD):  $0.003225
Output Cost (USD):  $0.007308
Thoughts Cost (USD):$0.074964
Total Cost (USD):   $0.099917


# Execution time in seconds:

89
