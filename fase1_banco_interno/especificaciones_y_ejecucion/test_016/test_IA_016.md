# Resumen ejecutivo

El problema más probable en producción es una combinación de runtime no soportado y timeouts por bloqueo bajo concurrencia. El repo no traía detalles del error, pero el código/config actual contiene regresiones claras que explican fallos típicos de Lambda/API Gateway.

## Hallazgos clave

- **Runtime de Lambda riesgoso:** la plantilla estaba configurada con `python3.13` (alto riesgo de no estar soportado en Lambda o en tooling/pipeline), lo que puede causar fallos de despliegue o invocación.
- **Bloqueos sin límite (deadlock/espera infinita):** el mecanismo de “reserva de recursos” en DynamoDB hacía reintentos indefinidos cuando el lock ya existía. En Lambda con `Timeout: 60`, esto deriva en timeouts y respuestas 5xx/504.
- **Locks persistentes (“zombies”):** aunque se guarda un campo `ttl`, la tabla actual se define como `AWS::Serverless::SimpleTable` sin TTL explícito; si un request muere a mitad, el lock puede quedar bloqueando futuras transacciones.
- **Dependencia externa no validada:** el flujo llama a un endpoint interno (`INTERNAL_PROC_ENDPOINT`) pero antes no frenaba la operación si esa verificación fallaba; esto puede aumentar errores y dejar locks colgados.

## Evidencia en historial (commits)

El último commit reemplazó un enfoque previo que incluía timeout y una tabla con TTL por uno nuevo con espera indefinida y tablas `SimpleTable`, introduciendo regresión operativa bajo carga/concurrencia.

## Acciones realizadas (mitigaciones)

- Ajusté el runtime de `python3.13` a `python3.12` en la plantilla.
- Implementé timeout + backoff para la adquisición de locks y una limpieza “best-effort” de locks expirados basada en `ttl`.
- Endurecí el handler para:
	- Responder 400 ante JSON inválido.
	- Cortar si falla la verificación del endpoint interno.
	- Responder 409 cuando el recurso está ocupado en vez de agotar el timeout de Lambda.

## Riesgos y recomendaciones

- Si el cliente ve errores intermitentes bajo carga, el foco debe ser: locks con timeout, TTL real en DynamoDB, y observabilidad (métricas/logs por `tx_id`).
- Recomendación operativa: confirmar en CloudWatch Logs si el síntoma principal es “Task timed out…” o errores de runtime/deploy; eso validará el diagnóstico rápidamente.