# Ticket — bw_test_016

**Título:** Transferencias bancarias bloqueadas indefinidamente

**Repositorio de código:** `codigo_evaluado_en_test/bw_test_016/`

## Reporte

2.- La aplicación realiza transferencias entre cuentas, a veces las cuentas quedan bloqueadas.
3.- La aplicación realiza transferencias entre cuentas, a veces las cuentas quedan bloqueadas. la aplicación deberia funcionar como sigue:
- La aplicacion expone endpoints en una api rest para realizar transferencias entre cuentas
- Antes de transferir debe generar un identificador de transaccion
- Se debe reservar los fondos y llamar a un servicio que valida la integridad de estos
- Posterior a la validacion se realiza la transferencia y se libera la reserva

## Instrucciones para el desarrollador

1. Identifica la causa raíz del problema descrito arriba.
2. Documenta brevemente (2-3 líneas) cuál es la causa raíz y en qué archivo/línea se origina.
3. Avisa al facilitador en cuanto tengas la causa raíz identificada (o al cumplirse el tiempo máximo asignado) para detener el cronómetro.

*No se incluye información adicional a propósito — el objetivo es reproducir un reporte de incidente tal como llegaría desde soporte o desde un usuario.*
