# Ticket — bw_test_012

**Título:** Inventario del producto muestra stock negativo

**Repositorio de código:** `codigo_evaluado_en_test/bw_test_012/`

## Reporte

2.- El inventario del producto SKU-7821 muestra -3 unidades disponibles (stock negativo)
3.- El inventario del producto SKU-7821 muestra -3 unidades disponibles (stock negativo)
- El usuario elige un producto.
- El sistema anota qué versión del stock está viendo el usuario.
- Al hacer clic en comprar, el sistema verifica: "¿Sigue habiendo la misma cantidad que cuando este usuario empezó?".
- Si alguien más ya compró reduciendo el stock, el sistema detiene la transacción y avisa la nueva cantidad o que ya no hay stock.
Resultado: El inventario se mantiene exacto y se informa la cantidad en “vivo” del stock para cada transacción, evitando ejecutar movimientos que lleven stock a negativo.

## Instrucciones para el desarrollador

1. Identifica la causa raíz del problema descrito arriba.
2. Documenta brevemente (2-3 líneas) cuál es la causa raíz y en qué archivo/línea se origina.
3. Avisa al facilitador en cuanto tengas la causa raíz identificada (o al cumplirse el tiempo máximo asignado) para detener el cronómetro.

*No se incluye información adicional a propósito — el objetivo es reproducir un reporte de incidente tal como llegaría desde soporte o desde un usuario.*
