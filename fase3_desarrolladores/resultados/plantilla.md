# Resultados pruebas BugWizard vs. manual

**Evaluador:** D2
**Fecha:** 09/10/2026

## Metodología

- 1 ticket con BugWizard, 1 sin BugWizard, intercalados.
- Cronómetro: inicio al leer ticket, fin al identificar causa raíz.
- Causa raíz: 2-3 líneas + archivo/línea exacto.

## Tabla de resultados

| Ticket | Método | Hora inicio | Hora fin | Duración | Causa raíz (2-3 líneas) | Archivo / línea | Notas |
|---|---|---|---|---|---|---|---|
| bw_test_004 | BugWizard | 13:04 | 13:08 | 4 min. | El timeout de la funcion es muy corto | bw_test_004/lambda_b/lambda_function.py | |
| bw_test_005 | Manual | 13:10 | 13:21 | 11 min. | No hay timeout en la llamada HTTP  | src/risk/app.py | |
| bw_test_006 | BugWizard | 13:23 | 13:26 | 3 min. | no se puede probar | | |
| bw_test_007 | BugWizard | 13:30 | 13:32 | 2 min. | problema en la logica del circuit breaker  | email-service/index.py | |
| bw_test_008 | Manual | 13:50 | 13:55 | 5 min. | Parece haber una condicion de carrera en el codigo.  | src/transfer-processor/app.ts | |
| bw_test_009 | Manual | 14:00 | 14:01 | 13 min. | no hay codigo en la carpeta  | | |
| bw_test_010 | Manual | 14:03 | 14:18 | 15 min. | problema del encoding  | src/handlers/email.ts | |
| bw_test_011 | BugWizard | 14:20 | 14:23 | 3 min. | problema del encoding  | src/handlers/email.ts | |
| bw_test_012 | Manual | 14:40 | 14:55 | 15 min. | cache interno con info desactualizada  | inventory_handler/app.py | |
| bw_test_013 | Manual | 15:00 | 14:16 | 16 min. | se acaban las conexiones  | app/db/database.py | |
| bw_test_014 | BugWizard | 15:30 | 15:33 | 3 Min. | llamada duplicada en la API, por reglas del event bridge | template.yaml |  |
| bw_test_015 | Manual | 15:45 | 15:55 | 10 Min.  | Problema en el prefijo en la funcion que borra | delete_photo/app.py |  |
| bw_test_016 | BugWizard | 16:15 | 16:18 | 3 Min. | Dos transacciones opuestas (A→B y B→A) se ejecutan simultáneamente resultando en Deadlock| transfer_funds.py | |
| bw_test_018 | Manual | 16:21 | 16:25 | 3 Min. | Se lanza excepcion en duro | send_to_warehouse.py |  |
| bw_test_019 | Manual | 16:27 | 16:47 | 20 min. | Demoras por mala configuracion de dynamo | product_service/app.py |  |
| bw_test_020 | Manual | 17:00 | 17:13 | 20 min. | Problemas en la configuracion de cors | src/handlers/profile_service.js |  |


## Resumen

| Método | Nº pruebas válidas | Duración promedio | Duración mín | Duración máx |
|---|---|---|---|---|
| BugWizard | | | | |
| Manual | | | | |

*Pruebas excluidas del cálculo por invalidez: 

## Observaciones generales

