# Resultados pruebas BugWizard vs. manual

**Evaluador:** D4
**Fecha:** 09/10/2026

## Metodología

- 1 ticket con BugWizard, 1 sin BugWizard, intercalados.
- Cronómetro: inicio al leer ticket, fin al identificar causa raíz.
- Causa raíz: 2-3 líneas + archivo/línea exacto.

## Tabla de resultados

| Ticket | Método | Hora inicio | Hora fin | Duración | Causa raíz (2-3 líneas) | Archivo / línea | Notas |
|---|---|---|---|---|---|---|---|
| bw_test_004 | Manual | 4:06 | 4:17 | 11 min. | La función Lambda tiene configurado un timeout de 10 sec y el proceso se queda pegado al tratar de asignar los permisos de cognito. Posiblemente 10 segundos no sean suficiente para integrarse a la API Externa https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/api/processor  | bw_test_004/lambda_b/lambda_function.py | Se deja fuera de scope la revision de la API mencionada catalogandola como externa |
| bw_test_005 | BugWizard | 13:23  | 13:26 | 3 Min.  | Idem que caso anterior, Llamada a API Externa con timeout no especificado | src/risk/app.py | La herramienta llegó a la conclusión mas rapido que yo en el caso anterior y entregó mas detalle pero no fue capaz de darme un resumen en 2 lineas. |
| bw_test_006 | Manual | 13:47 | 1:52 | 5min | - | - | Prueba no valida, canary falló |
| bw_test_007 | Manual | 13:58 | 2:02 | 4min.  | Cuota Amazon SES alcanzada, todos los servicios fallan al tratar de enviar email | * |  |
| bw_test_008 | BugWizard | 2:04 | 2:06 | 2min |  |  | Prueba no valida, BugWizard indica log vacío |
| bw_test_009 | BugWizard | 2:09 | 2:10 | 1min |  |  | Prueba no valida, proyecto no cargado en BugWizard |
| bw_test_010 | BugWizard | 2:11 | 2:13 |  2min | Charset mal configurado  | src/handlers/email.ts |  |
| bw_test_011 | Manual | 2:14 | 2:23 | 9 min | Excepcion mal manejada en funcion que envia correos | email_sender/app.py:27  | Sabia que habia temas con las excepciones pero no estaba seguro cual asi que tuve que usar claude |
| bw_test_012 | BugWizard | - | - | - | - | -  | Stack no encontrado en AWS |
| bw_test_013 | BugWizard | 10:45 | 10:47 | 2 Min. | Agente detectó mala gestión de conexiones a BD | app/db/database.py |  |
| bw_test_014 | Manual | 10:49 | 10:58 | 10 Min. | Se detecta llamada duplicada en la API, al no tener configurado mecanismos de seguridad para ataques masivos, registra dos veces el evento | -  |  |
| bw_test_015 | BugWizard | 11:12 | 11:14 | 2 Min.  | Problema en determinación de nombres (prefijos) al borrar | delete_photo/app.py |  |
| bw_test_016 | Manual | 11:15 | 11:16 | 1 Min. | Viendo el codigo se detecta falta de manejo de excepciones para liberar los recursos retenidos en proceso de transferencia (Falta Finally) | transfer_funds.py | Se omite revision de logs |
| bw_test_018 | BugWizard |  |  |  |  |  | Sin Logs encontrados por BugWizard |
| bw_test_019 | BugWizard |  |  |  |  |  | Sin Logs encontrados por BugWizard |
| bw_test_020 | BugWizard |  |  |  |  |  | Sin Logs encontrados por BugWizard |

## Resumen

| Método | Nº pruebas válidas | Duración promedio | Duración mín | Duración máx |
|---|---|---|---|---|
| BugWizard | 4 | 2.3 min | 2 min | 3 min |
| Manual | 5 | 7 min | 1 min | 11 min |

*Pruebas excluidas del cálculo por invalidez: bw_test_006, 008, 009, 012, 018, 019, 020 (7 en total — 6 BugWizard, 1 Manual).*

## Observaciones generales

- BugWizard resolvió más rápido en promedio (2.3 min vs. 7 min), pero tuvo alta tasa de invalidez (6/10 pruebas descartadas: logs vacíos, proyecto no cargado, stack no encontrado).
- bw_test_011 (Manual) quedó contaminado: se usó ayuda externa (Claude) para identificar la causa — su tiempo (9 min) no refleja un "manual puro".
- bw_test_016 (Manual, 1 min) se resolvió sin revisar logs — posible causa raíz encontrada más por intuición/lectura de código que por análisis completo; validar si aplica igual criterio que el resto.
- Sample size bajo por método tras excluir inválidas (4 BugWizard, 5 Manual) — cuidado al generalizar conclusiones para la tesis.
</content>
