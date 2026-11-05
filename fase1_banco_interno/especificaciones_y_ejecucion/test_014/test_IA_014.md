# Resultados obtenidos

## Hallazgos

- El template SAM tenía un problema serio de wiring: el mismo evento `PurchaseCompleted` podía invocar `UpdateLoyaltyPointsFunction` por dos caminos a la vez (un `AWS::Events::Rule` + el `Events: EventBridgeRule` dentro de la función). En producción eso se traduce típicamente en ejecuciones duplicadas (puntos doble-contados) y comportamiento “intermitente”.
- Además, el último commit agregaba `ReservedConcurrentExecutions: 1` a `UpdateLoyaltyPointsFunction`, lo que en carga real suele causar throttling (429/errores y reintentos), empeorando todavía más la duplicidad y la percepción de “falla”.
- En código había riesgo de error runtime por tipos: `points_earned` podía venir como string (p.ej. `"10"`) y terminar en `TypeError` al sumar con `int`.
- La actualización de puntos no era atómica (patrón `get_item` + `put_item`), así que con eventos repetidos o carreras era fácil perder/duplicar actualizaciones.

## Cambios listos para mitigar

- En `template.yaml` eliminé el trigger duplicado y quité la concurrencia reservada de 1.
- En `update_points.py` normalicé/parsié payload, forcé `points_earned` a `int` y cambié a `update_item` atómico.
- En `process_purchase.py` endurecí parseo JSON y manejo de fallos de `put_events`.

## Estado actual

Hay cambios locales en esos 3 archivos (tu `git status` ya los muestra). Si quieres, puedo prepararte el commit con un mensaje claro o generar un checklist de verificación en CloudWatch para confirmar que era esto lo que pasaba en prod.