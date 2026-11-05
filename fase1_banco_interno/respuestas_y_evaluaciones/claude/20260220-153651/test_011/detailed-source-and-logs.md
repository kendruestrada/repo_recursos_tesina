Con toda la información recopilada, puedo presentar el análisis completo:

---

## Envio de 5 correos duplicados para la misma orden

### Summary: El cliente recibe 5 correos identicos debido a la ausencia de idempotencia en el pipeline SQS + reintento automatico de mensajes fallidos.

### Severity: High

---

### Root Cause Analysis

**Pasos para reproducir**
1. El cliente (o un sistema externo) llama al endpoint de `ProcessOrderFunction` 5 veces con el mismo `order_id`, o el trigger se activa 5 veces por reintentos de red/API Gateway.
2. `ProcessOrderFunction` envia un mensaje a SQS por cada invocacion, sin verificar si el `order_id` ya fue procesado.
3. `EmailSenderFunction` recibe cada mensaje y envia el correo por cada uno.

**Expected vs Actual**
- Esperado: Un solo mensaje en SQS por `order_id`, un solo correo enviado.
- Actual: N mensajes en SQS por el mismo `order_id` → N correos enviados.

**Ubicacion del bug**

`process_order/app.py` — funcion `lambda_handler`, lineas 10–32:

```python
# No hay verificacion de si el order_id ya fue procesado
response = sqs.send_message(
    QueueUrl=QUEUE_URL, MessageBody=json.dumps(message_body)
)
```

Cada llamada a esta funcion produce un nuevo mensaje SQS con el mismo `order_id`, sin idempotencia.

**Segundo vector: SQS retry loop**

Los logs de `EmailSenderFunction` confirman que el mismo `order_id` es procesado repetidamente. El patron visible en CloudWatch (orden `0edf6c2d-f207-49ae-a70b-7c3a45f2eb85`):

```
13:00:30 - Orden recibida → Error → Exception lanzada → SQS NO elimina el mensaje
13:00:59 - Mismo mensaje reintentado → Error → Exception → SQS reintenta
13:01:29 - Mismo mensaje reintentado → Error → Exception → SQS reintenta
13:01:59 - Mismo mensaje reintentado → ...
13:02:29 - Mismo mensaje reintentado → ...
```

`email_sender/app.py:27` lanza una excepcion cuando el servicio de email retorna un error:

```python
raise Exception("Error al enviar correo")   # linea 27
```

Cuando Lambda lanza una excepcion, SQS **no elimina el mensaje** y lo reencola automaticamente. Si en alguno de esos reintentos el servicio de correo responde con 200 (intermitentemente), el correo se envia. Pero al no haber mecanismo de idempotencia, si el mensaje se reintenta y el servicio responde 200 nuevamente, se envia un segundo correo identico.

**Tercer vector: Bug en el nombre del campo**

`email_sender/app.py:18` envia el campo `email` pero el servicio espera `customer_email`:

```python
# Actual (incorrecto):
json={"email": email, "order_id": order_id, "amount": amount}

# El servicio responde:
# "Missing required fields: order_id, customer_email, amount"
```

Este bug causa que **todos** los intentos actuales fallen con 400, lo que activa el loop de reintentos de SQS indefinidamente hasta alcanzar `maxReceiveCount`.

---

### Solution

**1. Corregir el nombre del campo en `email_sender/app.py:18`**

```python
# Corregido:
json={"customer_email": email, "order_id": order_id, "amount": amount}
```

**2. Implementar idempotencia en `process_order/app.py`**

Antes de enviar el mensaje a SQS, verificar en una tabla DynamoDB (o similar) si el `order_id` ya fue procesado. Si existe registro, retornar sin encolar un nuevo mensaje.

```python
# Logica de idempotencia antes de sqs.send_message():
# - Verificar en DynamoDB si order_id ya existe
# - Si existe, retornar 200 sin encolar
# - Si no existe, encolar y registrar el order_id
```

**3. Implementar idempotencia en `email_sender/app.py`**

Antes de llamar al servicio de correo, verificar si ya fue enviado un correo para ese `order_id`. SQS garantiza entrega *al menos una vez* (at-least-once), por lo que el consumidor debe ser idempotente independientemente del origen del duplicado.

**4. Configurar Dead Letter Queue (DLQ)**

Definir un `maxReceiveCount` apropiado (ej. 3) y una DLQ en la cola SQS para evitar que mensajes fallidos se reintentan indefinidamente. Esto corta el loop de reintentos visible en los logs de `EmailSenderFunction`.

# Total cost USD

0.6173925

# Execution time in seconds: 

136
