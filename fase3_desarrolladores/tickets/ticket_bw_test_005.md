# Ticket — bw_test_005

**Título:** Solicitudes de crédito atascadas en estado 'en proceso'

**Repositorio de código:** `codigo_evaluado_en_test/bw_test_005/`

## Reporte

1.- Algunas solicitudes de crédito quedan 'en proceso' indefinidamente"     
2.- Algunas solicitudes de crédito quedan 'en proceso' indefinidamente", el flujo deberia se como sigue;
- un lambda recibe la solicitud y guarda el estado pending
- se consuta otro lambda para evaluar el riesgo
- una vez evaluado el riesgo se deberia actualizar el estado de la solicitud

## Instrucciones para el desarrollador

1. Identifica la causa raíz del problema descrito arriba.
2. Documenta brevemente (2-3 líneas) cuál es la causa raíz y en qué archivo/línea se origina.
3. Avisa al facilitador en cuanto tengas la causa raíz identificada (o al cumplirse el tiempo máximo asignado) para detener el cronómetro.

*No se incluye información adicional a propósito — el objetivo es reproducir un reporte de incidente tal como llegaría desde soporte o desde un usuario.*
