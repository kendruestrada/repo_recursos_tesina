## [Titulo]: Interrupcion de flujo de ordenes por error de bodega y actualizacion prematura de estado
### Resumen: El proceso de orden de compra no finaliza porque la API de la bodega retorna un error 503, activando una compensacion donde el reembolso falla, mientras que el estado de la orden queda erroneamente como completado.
### Severidad: Critical
### Analisis de causa raiz
- Pasos para reproducir:
  1. Enviar una solicitud de orden de compra al endpoint de la API.
  2. Verificar la ejecucion en Step Functions donde el pago se procesa y el inventario se actualiza.
  3. Observar la falla en el paso de bodega que evita el envio del correo de confirmacion.
  4. Revisar la fase de compensacion donde el reembolso no se procesa.
- Esperado vs. Actual:
  - Esperado: El estado de la orden solo se establece en completado al finalizar exitosamente todos los pasos (incluido el envio a bodega y el correo). En caso de error, el pago debe ser reembolsado.
  - Actual: La funcion de inventario actualiza prematuramente el estado de la orden a completado. Posteriormente, el envio a bodega falla con un error 503, impidiendo que el cliente reciba la confirmacion. El flujo de compensacion tambien falla debido a un error 429 en el reembolso, provocando que se cobre el dinero al cliente sin enviarle el producto.
- Ubicacion del error:
  - src/update_inventory.py (funcion handler)
  - src/send_to_warehouse.py (funcion handler)
  - src/refund_payment.py (funcion handler)
- Logs relevantes:
  - [ERROR] Exception: Warehouse API Error: 503 Service Unavailable - System under maintenance
  - Order status set to 'completed' (this is the bug!)
  - [ERROR] Exception: Payment Gateway Error: 429 Too Many Requests - Rate limit exceeded
  - CRITICAL: Payment was charged but refund FAILED!
### Propuesta de Solucion
1. Modificar src/update_inventory.py para remover la actualizacion del estado a completado, asegurando que el estado cambie unicamente al final de la ejecucion exitosa de la maquina de estados.
2. Manejar la excepcion en src/send_to_warehouse.py mediante una cola de mensajes muerta (DLQ) o suspender la operacion hasta que el sistema de bodega termine su mantenimiento, en lugar de fallar de manera forzosa despues de los reintentos.
3. Implementar un patron de reintentos con retardo exponencial (backoff) dentro de src/refund_payment.py o usar una cola asincrona para procesar reembolsos retrasados y asegurar la devolucion de fondos ante limites de peticiones (error 429).

# Token Usage

Total Tokens: 102672
Prompt Tokens: 98489
Input Tokens (non-cached): 37415
Response Tokens: 787
Cached Tokens: 61074
Thoughts Tokens: 3396

# Estimated Cost (model: gemini-3-pro-preview)

Input Cost (USD):   $0.074830
Cached Cost (USD):  $0.012215
Output Cost (USD):  $0.009444
Thoughts Cost (USD):$0.040752
Total Cost (USD):   $0.137241


# Execution time in seconds:

78
