# Resultados pruebas BugWizard vs. manual

**Evaluador:** D3
**Fecha:** 09/10/2026

## Metodología

- 1 ticket con BugWizard, 1 sin BugWizard, intercalados.
- Cronómetro: inicio al leer ticket, fin al identificar causa raíz.
- Causa raíz: 2-3 líneas + archivo/línea exacto.

## Tabla de resultados

| Ticket | Método | Hora inicio | Hora fin | Duración | Causa raíz (2-3 líneas) | Archivo / línea | Notas |
|---|---|---|---|---|---|---|---|
| bw_test_004 | Manual | 13:00 | 13:17 | 17 min. | timeout muy corto  | bw_test_004/lambda_b/lambda_function.py |  |
| bw_test_005 | BugWizard | 13:20  | 13:25 | 5 Min.  | al no especificar  timeout se toma el por defecto del lambda | src/risk/app.py | |
| bw_test_006 | Manual | 13:30 | 13:39 | 9min | Problema invalidacion de cache (se sirven datos desde el cache invalido) | cache_invalidation/app.py | - |
| bw_test_007 | Manual | 13:45 | 13:55 | 10min.  | la logica para impedit ThrottlingException esta mal implementada  | * |  |
| bw_test_008 | BugWizard | 13:59 | 14:05 | 6min | La transaccion debe ser atomica |  |  |
| bw_test_009 | BugWizard | - | - | - | El proy no existe en bw |  |  |
| bw_test_010 | BugWizard | 14:11 | 14:13 |  2min | Charset incorrectamente configurado  | src/handlers/email.ts |  |
| bw_test_011 | Manual | 14:15 | 14:25 | 10 min | Reintentos envian correos icorrectamente | email_sender/app.py:27  |  |
| bw_test_012 | BugWizard | - | - | - | - | -  | Stack no encontrado |
| bw_test_013 | BugWizard | 14:40 | 14:47 | 7 Min. | El pool de conexiones agota la conexiones por problema de implementacion | app/db/database.py |  |
| bw_test_014 | Manual | 14:49 | 14:59 | 10 Min. | PurchaseCompleted  invoca 2 veces a UpdateLoyaltyPointsFunction por reglas del event bridge | template.yaml |  |
| bw_test_015 | BugWizard | 15:12 | 15:15 | 3 Min.  | se determina incorrectamente el prefijo de los archivos a borrar | delete_photo/app.py |  |
| bw_test_016 | Manual | 15:20 | 15:36 | 16 Min. | Revisando codigo se determina que el problema es una race-condition |transfer_funds.py | |
| bw_test_018 | BugWizard | 16:02 | 16:05 | 3 Min. | excepcion hardcodeada | send_to_warehouse.py |  |
| bw_test_019 | BugWizard | 16:10 | 16:15 | 5 min. | Configuracion de dynamo no optimizada | product_service/app.py |  |
| bw_test_020 | BugWizard | 17:00 | 17:03 | 3 min. | Cors incorrecto | src/handlers/profile_service.js |  |


## Resumen

| Método | Nº pruebas válidas | Duración promedio | Duración mín | Duración máx |
|---|---|---|---|---|
| BugWizard | 8 | 4.3 min | 2 min | 7 min |
| Manual | 6 | 12.0 min | 9 min | 17 min |

*Pruebas excluidas del cálculo por invalidez: bw_test_009, bw_test_012 (2 en total — 2 BugWizard).*

## Observaciones generales
- En las pruebas manuales intenté encontrar los problemas solo, me fue mas fácil mirar solo el cádigo , ya que algunos se podian identificar facilmente.
