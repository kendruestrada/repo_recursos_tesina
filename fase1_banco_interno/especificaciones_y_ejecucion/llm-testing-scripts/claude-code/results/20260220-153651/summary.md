## Resumen de Ejecuciones

**19 pruebas | 57 ejecuciones totales** (3 modos por prueba)

---

### Metricas Globales

| Metrica | Valor |
|---|---|
| Tiempo total | 5162 seg / **86.0 min** |
| Tiempo promedio por ejecucion | 90.6 seg / **1.5 min** |
| Costo total | **$23.95 USD** |
| Costo promedio por ejecucion | **$0.42 USD** |

---

### Resumen por Prueba

| # | Bug | Severidad | Hallazgo principal | Tiempo (seg) | Costo (USD) |
|---|---|---|---|---|---|
| 001 | Compra fallida: address null | High | `validate-address` retorna HTTP 200 con `address:null` enmascarando error del proveedor externo | 247 | $1.69 |
| 002 | SavePayment | Critical/High | `package.json` con `"type":"module"` incompatible con CommonJS; respuesta del servicio externo ignorada, siempre persiste `"success"` | 211 | $0.89 |
| 003 | Prima del titular cero | High | Validacion `prima==0` aplicada solo a dependientes, no al titular; variable `BASE_COVERAGE` sin configurar | 232 | $1.15 |
| 004 | Sistema de suscripciones | Critical/High | `Timeout` como string en YAML; `StreamName` recibe ARN completo; `requests.get()` sin timeout bloquea asignacion Cognito | 299 | $1.07 |
| 005 | Inconsistencia tipo credit_id | Critical | `credit_id` guardado como String pero enviado como Number a RiskAnalysis; `requests.get()` sin timeout deja creditos en `pending` | 184 | $1.29 |
| 006 | Cache stale en checkout | Critical | `redis.delete()` ejecutado despues de llamada HTTP bloqueante; ventana de precio obsoleto causa rechazos falsos en checkout | 385 | $1.24 |
| 007 | Circuit Breaker invertido | Critical | Condicion `<` en lugar de `>=` hace que el breaker permita trafico durante el bloqueo y bloquee permanentemente al expirar | 474 | $1.48 |
| 008 | API Bancaria: race condition | Critical | TOCTOU en transferencias sin `ConditionExpression`; `TransferProcessorFunction` nunca invocada (codigo muerto); `HashKey` 40KB expuesto | 365 | $1.75 |
| 009 | Memory Leak en Lambda | Critical | `TEMPLATE_CACHE` global acumula listas crecientes (`N*100000` elementos) entre warm starts; `memorySize: 128` insuficiente | 220 | $0.87 |
| 010 | Registro de usuarios | High | `ConditionExpression` comentada permite sobrescribir usuarios; acceso a `.S` sin validacion causa TypeError no capturado; charset ASCII trunca tildes | 379 | $1.53 |
| 011 | Ordenes: duplicados y UnboundLocalError | High | `customer_email`/`amount` sin valor por defecto causan `UnboundLocalError`; campo `email` en lugar de `customer_email` en POST + `raise Exception` activa 5 reintentos SQS | 275 | $1.44 |
| 012 | Stock negativo: race condition | Critical | Cache interno nunca se actualiza tras escritura; `put_item` incondicional permite sobregiros concurrentes; `time.sleep(0.5)` amplifica la ventana | 187 | $0.78 |
| 013 | Connection pool exhaustion | Critical | `putconn()` ausente en flujo exitoso; semaforo se agota tras 5 invocaciones en mismo contenedor; 6ta invocacion bloquea indefinidamente | 193 | $1.11 |
| 014 | Puntos de fidelidad duplicados | High | `put_item` sobreescribe todos los atributos del usuario; dos reglas EventBridge identicas disparan Lambda dos veces por compra | 280 | $1.19 |
| 015 | Eliminacion masiva S3 | Critical | `rsplit('/', 1)[0]+'/'` construye prefijo del directorio raiz del usuario; borra todas las fotos en lugar de solo la solicitada | 180 | $0.77 |
| 016 | Deadlock en transferencias | Critical | Adquisicion de locks en orden variable crea espera circular; `while True` sin timeout en `reserve_resource` bloquea hasta timeout de Lambda | 156 | $1.11 |
| 017 | Saga Pattern: estado inconsistente | Critical | `UpdateInventory` marca orden `completed` prematuramente; `RevertInventory` no revierte `status`; `RefundPayment` lanza excepcion hardcodeada 100% | 204 | $2.03 |
| 018 | Paginacion ignorada / latencia | High | Parametro `page` recibido pero nunca usado en consulta DynamoDB; campo `data` de gran tamano fuerza multiples llamadas DynamoDB en serie | 483 | $1.59 |
| 019 | JWT/CORS bypass | Critical | JWT decodificado sin verificar firma; servidor refleja `Origin` dinamicamente con `Credentials:true`; API Gateway con `AllowOrigin:'*'` | 208 | $0.98 |

---

### Distribucion por Severidad

| Severidad | Cantidad de pruebas |
|---|---|
| Critical | 13 |
| High | 6 |

### Totales por Modo de Ejecucion

| Modo | Tiempo total (seg) | Costo total (USD) |
|---|---|---|
| source-only | 1375 | $4.53 |
| source-and-logs | 2195 | $10.74 |
| detailed-source-and-logs | 1592 | $8.68 |
