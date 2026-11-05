# Ticket — bw_test_018

**Título:** Orden marcada como 'completada' de forma inconsistente

**Repositorio de código:** `codigo_evaluado_en_test/bw_test_018/`

## Reporte

2.- La aplicación procesa ordenes de compra, pero los clientes no reciben confirmacion ni los productos son enviados a la bodega.
3.- La aplicación procesa ordenes de compra, pero los clientes no reciben confirmacion ni los productos son enviados a la bodega. la aplicación deberia funcionar como sigue:
- La aplicacion expone un endpoint en una api rest para procesar una orden de compra
- Se debe procesar el pago, luego actualizar el inventario, luego enviar el producto a la bodega, y finalmente notificar por correo electronico al usuario

## Instrucciones para el desarrollador

1. Identifica la causa raíz del problema descrito arriba.
2. Documenta brevemente (2-3 líneas) cuál es la causa raíz y en qué archivo/línea se origina.
3. Avisa al facilitador en cuanto tengas la causa raíz identificada (o al cumplirse el tiempo máximo asignado) para detener el cronómetro.

*No se incluye información adicional a propósito — el objetivo es reproducir un reporte de incidente tal como llegaría desde soporte o desde un usuario.*
