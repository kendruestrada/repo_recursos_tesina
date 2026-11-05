Con base en los logs y el código fuente, tengo un cuadro completo del problema. Aqui el análisis:

---

## [DUPLICADOS]: El cliente recibe 5 correos idénticos por la misma orden

### Summary: EmailSenderFunction lanza una excepcion al fallar, lo que impide que SQS elimine el mensaje y lo reintenta hasta 5 veces, enviando un correo en cada intento.

### Severity: High

---

### Root Cause Analysis

**Patrón observado en logs de `EmailSenderFunction`:**

Para la orden `a77a225e-5422-4ce3-b161-4968a588c399` se registran 5 invocaciones independientes (13:00:30, 13:00:59, 13:01:29, 13:01:59, 13:02:29), cada una con el mismo ciclo:

```
Orden recibida de SQS: a77a225e-...
Error al enviar correo para la orden a77a225e-...: {"message": "Missing required fields: order_id, customer_email, amount"}
[ERROR] Exception: Error al enviar correo
  File "/var/task/app.py", line 27, in lambda_handler
    raise Exception("Error al enviar correo")
```

**Dos bugs encadenados:**

**Bug 1 - Nombre de campo incorrecto** (`email_sender/app.py:17`):

```python
response = requests.post(
    EMAIL_SERVICE_URL,
    json={"email": email, "order_id": order_id, "amount": amount},  # incorrecto
)
```

El servicio de correo espera el campo `customer_email`, pero el codigo envia `email`. Por eso la respuesta es siempre `Missing required fields: order_id, customer_email, amount`. El correo puede enviarse con datos incompletos o el servicio lo procesa y devuelve error igualmente.

**Bug 2 - Excepcion lanzada ante fallo** (`email_sender/app.py:27`):

```python
else:
    print(f"Error al enviar correo para la orden {order_id}: {response.text}")
    raise Exception("Error al enviar correo")  # <-- este raise es el detonante de los reintentos
```

Cuando Lambda lanza una excepcion con un trigger SQS, **SQS interpreta la invocacion como fallida y NO elimina el mensaje de la cola**. Una vez vence el `visibilityTimeout`, el mensaje vuelve a ser visible y Lambda lo vuelve a procesar. Este ciclo se repite hasta alcanzar el `maxReceiveCount` de la cola (por defecto 5 si no hay DLQ configurada), lo que resulta en 5 invocaciones y 5 correos enviados.

**Flujo de ejecucion real:**

```
ProcessOrderFunction  →  envia 1 mensaje SQS
SQS                   →  entrega mensaje a EmailSenderFunction (intento 1)
EmailSenderFunction   →  llama email service → respuesta de error → raise Exception
SQS                   →  mensaje NO eliminado, vuelve a encolar tras visibilityTimeout
EmailSenderFunction   →  (intento 2) → mismo resultado
...                      (intento 3, 4, 5) → mismos resultados
Cliente               →  recibe 5 correos identicos
```

**Steps to reproduce:**
1. Enviar una orden que llega a `ProcessOrderFunction`
2. `EmailSenderFunction` falla (error del servicio de email)
3. SQS reintenta el mensaje hasta 5 veces
4. Cada reintento dispara un nuevo envio de correo

**Expected vs Actual:**
- Esperado: 1 correo por orden
- Actual: hasta 5 correos por orden (igual al `maxReceiveCount` de la cola SQS)

**Location of the bug:**
- `email_sender/app.py:17` — nombre de campo `email` en lugar de `customer_email`
- `email_sender/app.py:24-27` — el bloque `else` lanza una excepcion que activa los reintentos de SQS

---

### Solution

**Correccion 1 - Nombre de campo** (`email_sender/app.py:17`):
```python
# Cambiar:
json={"email": email, "order_id": order_id, "amount": amount}
# Por:
json={"customer_email": email, "order_id": order_id, "amount": amount}
```

**Correccion 2 - Idempotencia antes de relanzar excepcion:**

La excepcion puede ser necesaria para alertas/DLQ, pero se debe garantizar que el correo no se envie mas de una vez. Las opciones son:

- **Opcion A (recomendada):** Configurar una DLQ en la cola SQS y reducir `maxReceiveCount` a 1 si el servicio de email no es idempotente.
- **Opcion B:** Registrar en una tabla DynamoDB que el correo ya fue enviado usando `order_id` como clave, y verificar esa tabla antes de llamar al email service.
- **Opcion C:** Si el error es definitivo y no requiere reintento, capturar la excepcion sin relanzarla para que SQS elimine el mensaje:

```python
if response.status_code == 200:
    print(f"Correo enviado a {email} para la orden {order_id}")
else:
    print(f"Error al enviar correo para la orden {order_id}: {response.text}")
    # Solo relanzar si el error es transitorio (5xx), no en errores de cliente (4xx)
    if response.status_code >= 500:
        raise Exception("Error transitorio al enviar correo")
    # Para errores 4xx (como el campo incorrecto) no relanzar; el mensaje ira a DLQ
```

# Total cost USD

0.55019575

# Execution time in seconds: 

83
