## Análisis del Ticket de Soporte Técnico

**Ticket:** Revisión de errores en logs e identificación de causa raíz en el código fuente del sistema de procesamiento de pagos serverless.

## Hallazgos en los logs

### Errores principales identificados:

1. **Error de verificación de email en SES:**
   ```
   "An error occurred (MessageRejected) when calling the SendEmail operation: Email address is not verified. The following identities failed the check in region US-EAST-1: no-reply@example.com, customer@example.com"
   ```

2. **Activación del Circuit Breaker:**
   - Estado inicial: `"circuitBreakerState": "CLOSED", "failureCount": 1`
   - Progresión: failureCount incrementa hasta 5, 10, 16, 17, 18, 29, 30
   - Estado final: `"circuitBreakerState": "OPEN"`

3. **Respuestas de error HTTP:**
   - **504 Gateway Timeout**: Cuando SES falla por emails no verificados
   - **503 Service Unavailable**: Cuando el circuit breaker está abierto

4. **Patrón de comportamiento:**
   - Algunas respuestas exitosas: `"statusCode": 200, "body": "Email sent successfully"`
   - Fallos intermitentes que activan el circuit breaker

## Relación con el código fuente

### 1. **Función `external_status_check()` en EmailService**

**Problema identificado:** La función está configurada para fallar intencionalmente:

```python
def external_status_check():
    url = os.environ.get('STATUS_CHECK_URL')
    try:
        print(f"Requesting external status check...")
        with urllib.request.urlopen(url, timeout=2) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"External check unavailable: {str(e)}")  
        return False  # ← CAUSA RAÍZ: Siempre retorna False en caso de error
```

### 2. **Lógica del Circuit Breaker defectuosa**

**Problema en la implementación:**

```python
def call(self, func, *args, **kwargs):
    if self.state == "OPEN":
        if time.time() < self.last_failure_time + self.recovery_timeout:  # ← ERROR LÓGICO
            self.state = "HALF-OPEN"
            print("Transition to HALF-OPEN state.")
        else:
            raise Exception("Circuit breaker is OPEN - all requests blocked")
```

**Error:** La condición debería ser `>=` en lugar de `<` para permitir la transición a HALF-OPEN después del timeout.

### 3. **Configuración de SES en modo mock**

```python
def send_email_via_ses(order_id, email, notification_type="EMAIL"):
    is_healthy = external_status_check()  # ← Siempre retorna False
    
    if not is_healthy:
        error_response = {
            'Error': {
                'Code': 'ServiceUnavailable', 
                'Message': 'The request has failed due to a temporary failure of the service.'
            }
        }
        raise ClientError(error_response, 'SendEmail')  # ← Genera el error 504
```

## Ejemplo de ejecución

### Simulación del flujo defectuoso:

```python
# Estado inicial
circuit_breaker.state = "CLOSED"
circuit_breaker.failure_count = 0

# Request 1-4: Fallan por external_status_check() = False
for i in range(1, 5):
    try:
        is_healthy = external_status_check()  # Returns False
        # Lanza ClientError, incrementa failure_count
        circuit_breaker.failure_count += 1
        # Estado sigue "CLOSED"
    except:
        return 504

# Request 5: Circuit breaker se abre
circuit_breaker.failure_count = 5
circuit_breaker.state = "OPEN"
circuit_breaker.last_failure_time = time.time()

# Request 6+: Bloqueadas por circuit breaker
if circuit_breaker.state == "OPEN":
    # Condición incorrecta impide recuperación
    if time.time() < last_failure_time + 5:  # Siempre True inicialmente
        # Nunca llega aquí por la lógica invertida
        pass
    else:
        raise Exception("Circuit breaker is OPEN")  # 503 error
```

## Soluciones propuestas

### 1. **Corregir la lógica del Circuit Breaker**

```python
def call(self, func, *args, **kwargs):
    if self.state == "OPEN":
        # CORRECCIÓN: Cambiar < por >=
        if time.time() >= self.last_failure_time + self.recovery_timeout:
            self.state = "HALF_OPEN"
            print("Transition to HALF-OPEN state.")
        else:
            raise Exception("Circuit breaker is OPEN - all requests blocked")
```

### 2. **Configurar STATUS_CHECK_URL correctamente**

```bash
# Agregar variable de entorno válida o implementar mock exitoso
aws lambda update-function-configuration \
  --function-name EmailServiceFunction \
  --environment Variables='{
    "STATUS_CHECK_URL": "https://httpbin.org/status/200",
    "SENDER_EMAIL": "verified-email@yourdomain.com"
  }'
```

### 3. **Verificar emails en SES**

```bash
# Verificar el email remitente en SES
aws ses verify-email-identity --email-address no-reply@yourdomain.com

# O usar SES Sandbox con emails verificados
aws ses verify-email-identity --email-address customer@example.com
```

### 4. **Implementar fallback en external_status_check**

```python
def external_status_check():
    url = os.environ.get('STATUS_CHECK_URL')
    if not url:
        return True  # Fallback: asumir healthy si no hay URL configurada
    
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200
    except Exception as e:
        print(f"External check unavailable: {str(e)}")
        # OPCIÓN: Retornar True para permitir operación en caso de fallo del health check
        return os.environ.get('FALLBACK_HEALTHY', 'false').lower() == 'true'
```

### 5. **Agregar logging mejorado para debugging**

```python
def debug(self):
    current_time = time.time()
    recovery_time = self.last_failure_time + self.recovery_timeout if self.last_failure_time else None
    print(f"Circuit Breaker Debug:")
    print(f"  State: {self.state}")
    print(f"  Failure Count: {self.failure_count}")
    print(f"  Current Time: {current_time}")
    print(f"  Last Failure: {self.last_failure_time}")
    print(f"  Recovery Time: {recovery_time}")
    print(f"  Can Recover: {current_time >= recovery_time if recovery_time else 'N/A'}")
```

La causa raíz principal es la combinación de la función `external_status_check()` que siempre falla y la lógica incorrecta del circuit breaker que impide la recuperación automática del servicio.