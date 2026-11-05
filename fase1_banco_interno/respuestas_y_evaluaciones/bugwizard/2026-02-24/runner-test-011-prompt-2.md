## Análisis del Ticket de Soporte

**Ticket:** El cliente recibió 5 emails de confirmación de compra idénticos para la misma orden, cuando debería recibir únicamente un correo por transacción.

## Hallazgos en los logs

Analizando los logs de CloudWatch, se identifican varios patrones críticos:

1. **Múltiples ejecuciones para la misma orden:**
```
✅ Orden recibida de SQS: 5ec2397f-fc67-43c4-9586-4f56d0bb9f75
❌ Error al enviar correo para la orden 5ec2397f-fc67-43c4-9586-4f56d0bb9f75
```
La misma orden aparece procesada múltiples veces en diferentes RequestIds.

2. **Errores consistentes en el servicio de email:**
```
❌ Error al enviar correo para la orden [ID]: {"message": "Missing required fields: order_id, customer_email, amount"}
[ERROR] Exception: Error al enviar correo
```

3. **Patrón de reintentos automáticos:**
Los logs muestran que cada fallo genera una nueva ejecución de la Lambda, indicando que SQS está reintentando el procesamiento del mensaje.

## Relación con el código fuente

### Problema Principal en `email_sender/app.py`:

```python
def lambda_handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        order_id = body["order_id"]
        email = body["customer_email"]  # ❌ Falla si no existe
        amount = body["amount"]         # ❌ Falla si no existe
        
        # ... código de envío ...
        
        if response.status_code == 200:
            print(f"📧 Correo enviado a {email} para la orden {order_id}")
        else:
            print(f"❌ Error al enviar correo para la orden {order_id}: {response.text}")
            raise Exception("Error al enviar correo")  # ❌ CAUSA RAÍZ
```

### Problema Secundario en `process_order/app.py`:

```python
def lambda_handler(event, context):
    # ... código ...
    
    if "customer_email" in body:
        customer_email = body["customer_email"]
    
    if "amount" in body:
        amount = body["amount"]
    
    # ❌ Variables pueden quedar sin inicializar si no están en el body
    message_body = {
        "order_id": order_id,
        "customer_email": customer_email,  # ❌ UnboundLocalError posible
        "amount": amount,                  # ❌ UnboundLocalError posible
    }
```

## Ejemplo de ejecución

**Escenario problemático:**
1. Se envía una orden con body: `{"order_id": "123"}`
2. `process_order` intenta acceder a `customer_email` y `amount` no definidos
3. El mensaje llega a SQS con campos faltantes
4. `email_sender` falla al acceder a `body["customer_email"]`
5. Se lanza excepción, SQS reintenta el mensaje
6. El ciclo se repite hasta agotar los reintentos (5 veces según configuración)
7. Si eventualmente el servicio de email responde correctamente, se envían múltiples correos

## Soluciones propuestas

### Solución 1: Validación y manejo de errores en `email_sender/app.py`

```python
import json
import os
import requests

EMAIL_SERVICE_URL = os.environ["EMAIL_SERVICE_URL"]

def lambda_handler(event, context):
    processed_orders = set()  # Evitar duplicados en el mismo batch
    
    for record in event["Records"]:
        try:
            body = json.loads(record["body"])
            
            # Validación de campos requeridos
            required_fields = ["order_id", "customer_email", "amount"]
            missing_fields = [field for field in required_fields if field not in body]
            
            if missing_fields:
                print(f"❌ Campos faltantes en orden: {missing_fields}")
                continue  # No reintenta, marca como procesado
            
            order_id = body["order_id"]
            email = body["customer_email"]
            amount = body["amount"]
            
            # Evitar duplicados en el mismo batch
            if order_id in processed_orders:
                print(f"⚠️ Orden {order_id} ya procesada en este batch")
                continue
                
            processed_orders.add(order_id)
            print(f"✅ Orden recibida de SQS: {order_id}")
            
            response = requests.post(
                EMAIL_SERVICE_URL,
                json={"email": email, "order_id": order_id, "amount": amount},
                timeout=30
            )

            if response.status_code == 200:
                print(f"📧 Correo enviado a {email} para la orden {order_id}")
            else:
                print(f"❌ Error al enviar correo para la orden {order_id}: {response.text}")
                # No lanzar excepción para evitar reintentos infinitos
                
        except Exception as e:
            print(f"❌ Error procesando mensaje: {str(e)}")
            # Log del error pero no reintenta
            
    return {"status": "success"}
```

### Solución 2: Corrección en `process_order/app.py`

```python
import json
import os
import boto3
import uuid

sqs = boto3.client("sqs")
QUEUE_URL = os.environ["QUEUE_URL"]

def lambda_handler(event, context):
    try:
        body = json.loads(event["body"])
        
        # Validación de campos requeridos
        required_fields = ["customer_email", "amount"]
        missing_fields = [field for field in required_fields if field not in body]
        
        if missing_fields:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Missing required fields: {missing_fields}"
                })
            }
        
        order_id = body.get("order_id", str(uuid.uuid4()))
        customer_email = body["customer_email"]
        amount = body["amount"]

        message_body = {
            "order_id": order_id,
            "customer_email": customer_email,
            "amount": amount,
        }

        response = sqs.send_message(
            QueueUrl=QUEUE_URL, 
            MessageBody=json.dumps(message_body)
        )

        print(f"Orden procesada. Mensaje enviado a SQS ID: {response['MessageId']}")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Orden enviada", "order_id": order_id}),
        }
        
    except Exception as e:
        print(f"Error procesando orden: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Error interno del servidor"})
        }
```

### Solución 3: Configuración adicional en `template.yaml`

```yaml
EmailSenderFunction:
  Type: AWS::Serverless::Function
  Properties:
    # ... otras propiedades ...
    ReservedConcurrencyLimit: 1  # Limitar concurrencia
    Events:
      SQSEvent:
        Type: SQS
        Properties:
          Queue: !GetAtt OrdersQueue.Arn
          BatchSize: 1
          MaximumBatchingWindowInSeconds: 5  # Agregar ventana de batching
```

**Causa raíz identificada:** La combinación de campos faltantes en los mensajes SQS y el manejo inadecuado de excepciones causa reintentos automáticos que resultan en múltiples envíos de correo para la misma orden.