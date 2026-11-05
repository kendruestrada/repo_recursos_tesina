# Respuestas de la IA

Se ejecutaron dos consultas a la IA la cual genero las siguientes respuestas:

## Hallazgos

Encontré 2 problemas de configuración/código que típicamente rompen la Lambda:

- En la plantilla SAM, `CodeUri` apuntaba a `internal_services` pero las dependencias están en el `package.json` de la raíz; eso suele desplegar la función sin `node_modules` y falla con “Cannot find module…”.
- `package.json` tenía `"type": "module"` (ESM) pero el handler usa CommonJS (`require`, `exports.handler`), lo que puede fallar en Node 18.

## Fixes aplicados

Apliqué fixes mínimos:

- En `template.yaml` cambié a `CodeUri: ./` y `Handler: src/internal_services/SavePayment.handler`.
- En `package.json` removí `"type": "module"`.
- En `SavePayment.js` agregué validaciones para que si faltan env vars o el servicio externo responde mal, devuelva `500/502` con logs claros en vez de crashear.

## Posibles problemas de runtime

Como me dijiste que ya corre en producción, lo más probable es un problema “más específico” de runtime:

- **Timeout**: no hay `Timeout` en la función (default 3s) y el handler hace 2 `fetch` + 1 write a DynamoDB → puede dar `504` o “Task timed out”.
- **CORS** si lo llama un navegador: no se devuelven headers CORS.
- **Parámetro**: solo acepta `transaction_id` en query string; si llega distinto, responde `400`.