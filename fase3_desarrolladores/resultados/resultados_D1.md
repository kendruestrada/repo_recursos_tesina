# Resultados pruebas BugWizard vs. manual

**Evaluador:** D1
**Fecha:** 09/10/2026

## Metodología

- 1 ticket con BugWizard, 1 sin BugWizard, intercalados.
- Cronómetro: inicio al leer ticket, fin al identificar causa raíz.
- Causa raíz: 2-3 líneas + archivo/línea exacto.

## Tabla de resultados

| Ticket | Método | Hora inicio | Hora fin | Duración | Causa raíz (2-3 líneas) | Archivo / línea | Notas |
|---|---|---|---|---|---|---|---|
| bw_test_004 | BugWizard | 13:30 | 13:35 | 5 min. | Problema con el timeout de la funcion | bw_test_004/lambda_b/lambda_function.py | |
| bw_test_005 | Manual | 13:40 | 13:55 | 15 min. | En la llamada HTTP no exite timeout  | src/risk/app.py | |
| bw_test_006 | BugWizard | 14:00 | 14:04 | 4 min. | no aplica | | |
| bw_test_007 | BugWizard | 14:05 | 14:08 | 3 min. | logica del circuit breaker esta mal se debe cambiar la condicion  | email-service/index.py | |
| bw_test_008 | Manual | 14:10 | 14:25 | 15 min. | Cuando ocurren peticiones simultaneas no se manejan bien.  | src/transfer-processor/app.ts | |
| bw_test_009 | Manual | - | - | - | sin codigo  | | |
| bw_test_010 | Manual | 14:30 | 14:46 | 16 min. | character set incorrecto  | src/handlers/email.ts | |
| bw_test_011 | BugWizard | 14:50 | 14:55 | 5 min. | Sistema de reintentos manda el correo por cada reintento  | src/handlers/email.ts | |
| bw_test_012 | Manual | 15:04 | 15:25 | 21 min. | info desactualizada en el cache  | inventory_handler/app.py | |
| bw_test_013 | Manual | 15:30 | 15:46 | 16 min. | conexion pool mal implementado  | app/db/database.py | |
| bw_test_014 | BugWizard | 15:50 | 15:53 | 3 Min. | reglas del event bridge provocan dupolicidad de llamadas | template.yaml |  |
| bw_test_015 | Manual | 16:00 | 16:19 | 19 Min.  | la código que borra toma mal el prefijo por eso borra todos los archivos | delete_photo/app.py |  |
| bw_test_016 | BugWizard | 16:25 | 16:28 | 3 Min. | Deadlock por llamadas simultaneas| transfer_funds.py | |
| bw_test_018 | Manual | 16:30 | 16:35 | 5 Min. | excepcion en duro | send_to_warehouse.py |  |
| bw_test_019 | Manual | 16:40 | 16:57 | 17 min. | configuracion de dynamo provoca las deemoras | product_service/app.py |  |
| bw_test_020 | Manual | 17:00 | 17:20 | 20 min. |  cors mal configurado | src/handlers/profile_service.js |  |


## Resumen

| Método | Nº pruebas válidas | Duración promedio | Duración mín | Duración máx |
|---|---|---|---|---|
| BugWizard | 5 | 3.8 min | 3 min | 5 min |
| Manual | 9 | 16.0 min | 5 min | 21 min |

*Pruebas excluidas del cálculo por invalidez: bw_test_006, bw_test_009 (2 en total — 1 BugWizard, 1 Manual).*

## Observaciones generales
- Es lenta la revision manual principalmente por el acceso a aws, y encontrar el log adecuado.
- Use IA (claude) en las pruebas manuales si no encontraba la respuesta solo despues de 10 min.
