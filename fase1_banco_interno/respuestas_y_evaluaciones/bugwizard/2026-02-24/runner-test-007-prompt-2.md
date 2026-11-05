## **Ticket:** 
Aplicación completamente caída - Los servicios OrderProcessing, PaymentConfirmation y EmailService responden con error

## **Hallazgos en los logs:**

### 1. **Error principal identificado:**
```
"An error occurred (MessageRejected) when calling the SendEmail operation: Email address is not verified. The following identities failed the check in region US-EAST-1: no-reply@example.com, test@mail.com"
```

### 2. **Patrón de comportamiento del Circuit Breaker:**
- **Estado inicial:** `"circuitBreakerState": "CLOSED"` con `"failureCount": 1, 2, 3...`
- **Transición a OPEN:** Después de 5 fallos consecutivos: `"circuitBreakerState": "OPEN"`
- **Bloqueo total:** Una vez abierto, todas las peticiones son rechazadas con:
  ```
  "Circuit breaker is OPEN - all requests blocked"
  ```

### 3. **Códigos de error observados:**
- **504 Gateway Timeout:** Cuando SES rechaza emails por direcciones no verificadas
- **503 Service Unavailable:** Cuando el circuit breaker está OPEN y bloquea todas las peticiones

### 4. **Cascada de fallos:**
Los logs muestran que el fallo se propaga desde EmailService → OrderProcessing → PaymentConfirmation, causando que toda la cadena de servicios falle.

## **Relación con el código fuente:**

### 1. **EmailService - Causa raíz (lambda/email-service/index.py):**

**Problema principal:** El circuit breaker está configurado incorrectamente y la verificación de estado externo siempre falla.

```python
# Línea 25-27: Circuit breaker mal configurado
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=5)

# Línea 45-50: Verificación de estado que siempre falla
def send_email_via_ses(order_id, email, notification_type="EMAIL"):
    is_healthy = external_status_check()  # Siempre retorna False
    
    if not is_healthy:
        # Esto siempre se ejecuta, causando el error
        error_response = {
            'Error': {
                'Code': 'ServiceUnavailable', 
                'Message': 'The request has failed due to a temporary failure of the service.'
            }
        }
        raise ClientError(error_response, 'SendEmail')
```

**Función problemática:**
```python
# Líneas 118-125: Esta función siempre falla
def external_status_check():
    url = os.environ.get('STATUS_CHECK_URL')  # Probablemente None o URL inválida
    try:
        print(f"Requesting external status check...")
        with urllib.request.urlopen(url, timeout=2) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"External check unavailable: {str(e)}")  
        return False  # Siempre retorna False
```

### 2. **Circuit Breaker defectuoso:**

```python
# Líneas 13-24: Lógica del circuit breaker con error
def call(self, func, *args, **kwargs):
    if self.state == "OPEN":
        if time.time() < self.last_failure_time + self.recovery_timeout:  # ERROR LÓGICO
            self.state = "HALF-OPEN"  # Nunca se ejecuta por condición incorrecta
        else:
            raise Exception("Circuit breaker is OPEN - all requests blocked")
```

**Error crítico:** La condición `time.time() < self.last_failure_time + self.recovery_timeout` debería ser `>=` para permitir la recuperación.

## **Ejemplo de ejecución:**

```python
# Simulación del flujo de error:

# 1. EmailService recibe petición
order_id = "ORDER-123"
email = "test@mail.com"

# 2. external_status_check() falla
url = os.environ.get('STATUS_CHECK_URL')  # None o URL inválida
# Resultado: return False

# 3. Se lanza ClientError
error_response = {
    'Error': {
        'Code': 'ServiceUnavailable', 
        'Message': 'The request has failed due to a temporary failure of the service.'
    }
}
raise ClientError(error_response, 'SendEmail')

# 4. Circuit breaker incrementa failure_count
circuit_breaker.failure_count += 1  # 1, 2, 3, 4, 5...

# 5. Después de 5 fallos, circuit breaker se abre
if circuit_breaker.failure_count >= 5:
    circuit_breaker.state = "OPEN"

# 6. Todas las peticiones subsecuentes son bloqueadas
# Resultado: 503 Service Unavailable para toda la aplicación
```

## **Solución o soluciones propuestas:**

### **Solución Inmediata (Crítica):**

1. **Corregir la lógica del Circuit Breaker:**
```python
# En lambda/email-service/index.py, línea ~17
def call(self, func, *args, **kwargs):
    if self.state == "OPEN":
        # CORREGIR: Cambiar < por >=
        if time.time() >= self.last_failure_time + self.recovery_timeout:
            self.state = "HALF-OPEN"
            print("Transition to HALF-OPEN state.")
        else:
            raise Exception("Circuit breaker is OPEN - all requests blocked")
```

2. **Deshabilitar temporalmente la verificación externa:**
```python
# Modificar send_email_via_ses para bypass temporal
def send_email_via_ses(order_id, email, notification_type="EMAIL"):
    # TEMPORAL: Comentar la verificación que falla
    # is_healthy = external_status_check()
    # if not is_healthy:
    #     error_response = {...}
    #     raise ClientError(error_response, 'SendEmail')
    
    # Continuar con el envío normal de SES
    ses_client = boto3.client('ses')
    # ... resto del código
```

### **Solución Permanente:**

1. **Configurar correctamente STATUS_CHECK_URL:**
```bash
# Actualizar variable de entorno en Lambda
aws lambda update-function-configuration \
  --function-name EmailServiceFunction \
  --environment Variables={STATUS_CHECK_URL=https://status.aws.amazon.com/}
```

2. **Mejorar la función external_status_check:**
```python
def external_status_check():
    url = os.environ.get('STATUS_CHECK_URL')
    if not url:
        print("STATUS_CHECK_URL not configured, assuming healthy")
        return True  # Default a healthy si no está configurado
    
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                return True
            return False
    except Exception as e:
        print(f"External check failed: {str(e)}")
        return True  # Fail-open en lugar de fail-closed
```

3. **Resetear el Circuit Breaker:**
```bash
# Forzar reset actualizando la función
aws lambda update-function-configuration \
  --function-name EmailServiceFunction \
  --environment Variables={RESET=true}
```

### **Verificación de SES:**
```bash
# Verificar direcciones de email en SES
aws ses verify-email-identity --email-address no-reply@example.com
aws ses verify-email-identity --email-address test@mail.com
```

**Prioridad:** La aplicación se recuperará inmediatamente después de aplicar la corrección del circuit breaker y deshabilitar temporalmente la verificación externa defectuosa.