# Alcance revisado

- **Infra SAM**: `template.yaml`, `samconfig.toml`
- **Lambdas**: `app.py` y `app.py`
- **Dependencias**: `requirements.txt`

## Hallazgos principales

### 1) Bug en validación de payload (causa probable de crash en API)

En `app.py`, las variables `customer_email` y `amount` se asignan solo si existen en el JSON; si el request no trae alguno de esos campos, el código igual los usa al armar `message_body`, provocando un error tipo `UnboundLocalError` y fallando la ejecución.

**Impacto**: respuestas **5xx/502** en API Gateway para ciertos payloads (fallo “intermitente” según datos enviados).

### 2) Riesgo de permisos insuficientes para consumir SQS (causa probable de “no procesa mensajes”)

En `template.yaml`, `EmailSenderFunction` está disparada por SQS pero solo tiene `AWSLambdaBasicExecutionRole`. En un despliegue típico, eso no incluye permisos `sqs:ReceiveMessage` / `sqs:DeleteMessage` / `sqs:GetQueueAttributes`, por lo que puede haber `AccessDenied` y la cola se acumula sin ser consumida.

**Impacto**: la API puede “funcionar” (manda a SQS), pero no se envían correos porque la Lambda consumidora no logra leer/borrar mensajes.

## Recomendaciones (fixes concretos)

### Fix 1 (código)

Robustecer `app.py` para:

- Validar que exista `body` y sea JSON válido; si no, responder **400**.
- Validar campos requeridos (`customer_email`, `amount`); si faltan, responder **400** con mensaje claro.
- (Opcional) Leer `QUEUE_URL` con `os.getenv` dentro del handler y devolver **500** si no está configurado, evitando fallos en import-time.

### Fix 2 (infra/IAM)

En `template.yaml`, agregar policy de polling de SQS a `EmailSenderFunction` (p.ej. `SQSPollerPolicy` apuntando a `OrdersQueue`) para permitir consumir la cola correctamente.

## Cómo verificar rápidamente

- Enviar un POST a `/v1/report` sin `customer_email` o sin `amount` y revisar CloudWatch Logs: debería reproducirse el crash actual del handler.
- Revisar métricas/logs de `EmailSenderFunction` y DLQ/cola: si hay `AccessDenied` o crecimiento de `ApproximateNumberOfMessagesVisible`, confirma el problema de permisos SQS.