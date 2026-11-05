# Ticket — bw_test_008

**Título:** Transferencias entre cuentas: el dinero 'desaparece'

**Repositorio de código:** `codigo_evaluado_en_test/bw_test_008/`

## Reporte

2.- Al transferir fondos entre cuentas, a veces el dinero 'desaparece'
3.- Al transferir fondos entre cuentas, a veces el dinero 'desaparece, Flujo correcto de aplicación:
- El usuario solicita la transferencia.
- El sistema "congela" ambas cuentas en una sola operación.
- El dinero sale de una y entra en la otra simultáneamente.
- Cualquier revisión de saldo espera a que movimientos terminen antes de mostrar la información.
Resultado: El dinero nunca desaparece de la vista del sistema ni del usuario.

## Instrucciones para el desarrollador

1. Identifica la causa raíz del problema descrito arriba.
2. Documenta brevemente (2-3 líneas) cuál es la causa raíz y en qué archivo/línea se origina.
3. Avisa al facilitador en cuanto tengas la causa raíz identificada (o al cumplirse el tiempo máximo asignado) para detener el cronómetro.

*No se incluye información adicional a propósito — el objetivo es reproducir un reporte de incidente tal como llegaría desde soporte o desde un usuario.*
