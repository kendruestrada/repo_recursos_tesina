# Ticket — bw_test_020

**Título:** Posible fuga de datos de sesión desde sitios externos

**Repositorio de código:** `codigo_evaluado_en_test/bw_test_020/`

## Reporte

2.- La aplicación valida que un usuario tenga una sesion activa registrada en base de datos. El equipo de ciberseguridad ha reportado que la informacion de la sesion se puede obtener desde sitios sospechosos externos.
3.- La aplicación valida que un usuario tenga una sesion activa registrada en base de datos. El equipo de ciberseguridad ha reportado que la informacion de la sesion se puede obtener desde sitios sospechosos externos. la aplicación deberia funcionar como sigue:
- La aplicacion expone un endpoint en una api rest para validar que un usuario tenga una sesion activa
- Las sesiones activas se validan contra una base de datos
- La aplicacion utiliza tokens jwt y deben ser validados para utilizar el servicio

## Instrucciones para el desarrollador

1. Identifica la causa raíz del problema descrito arriba.
2. Documenta brevemente (2-3 líneas) cuál es la causa raíz y en qué archivo/línea se origina.
3. Avisa al facilitador en cuanto tengas la causa raíz identificada (o al cumplirse el tiempo máximo asignado) para detener el cronómetro.

*No se incluye información adicional a propósito — el objetivo es reproducir un reporte de incidente tal como llegaría desde soporte o desde un usuario.*
