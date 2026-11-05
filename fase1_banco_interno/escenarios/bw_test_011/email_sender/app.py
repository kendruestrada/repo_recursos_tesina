import json
import os
import requests

EMAIL_SERVICE_URL = os.environ["EMAIL_SERVICE_URL"]


def lambda_handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        order_id = body["order_id"]
        email = body["customer_email"]
        amount = body["amount"]

        print(f"✅ Orden recibida de SQS: {order_id}")
        response = requests.post(
            EMAIL_SERVICE_URL,
            json={"email": email, "order_id": order_id, "amount": amount},
        )

        if response.status_code == 200:
            print(f"📧 Correo enviado a {email} para la orden {order_id}")
        else:
            print(
                f"❌ Error al enviar correo para la orden {order_id}: {response.text}"
            )
            raise Exception("Error al enviar correo")

    return {"status": "success"}
