# Análisis del Ticket de Soporte Técnico

## **Ticket:** 
Aplicación completamente caída - Se requiere identificar la causa raíz mediante análisis de logs y código fuente.

## **Hallazgos en los logs:**

### Errores Críticos Identificados:

1. **Error principal de SES (Simple Email Service):**
   ```
   "An error occurred (MessageRejected) when calling the SendEmail operation: Email address is not verified. The following identities failed the check in region US-EAST-1: no-reply@example.com, test@mail.com"
   ```

2. **Patrón de fallas del Circuit Breaker:**
   - El circuit breaker está configurado con un umbral de 5 fallas
   - Se observa progresión: `failureCount: 1` → `failureCount: 2` → ... → `failureCount: 30`
   - Estado del circuit breaker: `CLOSED` → `OPEN`
   - Una vez abierto, todas las solicitudes son bloqueadas con error 503

3. **Códigos de estado HTTP problemáticos:**
   - **504 Gateway Timeout**: Cuando SES falla por emails no verificados
   - **503 Service Unavailable**: Cuando el circuit breaker está abierto

## **Relación con el código fuente:**

### Problema en `lambda/email-service/index.py`:

1. **Configuración de emails no verificados:**
   ```python
   Source=os.environ.get('SENDER_EMAIL', 'no-reply@example.com')
   ```
   El email por defecto `no-reply@example.com` no está verificado en AWS SES.

2. **Lógica del Circuit Breaker defectuosa:**
   ```python
   def call(self, func, *args, **kwargs):
       if self.state == "OPEN":
           if time.time() < self.last_failure_time + self.recovery_timeout:
               self.state = "HALF-OPEN"  # Error lógico aquí
           else:
               raise Exception("Circuit breaker is OPEN - all requests blocked")
   ```
   
   **Error crítico**: La condición está invertida. Debería ser `>=` en lugar de `<`.

3. **Función de verificación externa siempre falla:**
   ```python
   def external_status_check():
       url = os.environ.get('STATUS_CHECK_URL')
       # Si STATUS_CHECK_URL no está configurada, url será None
       # urllib.request.urlopen(None) siempre fallará
   ```

## **Ejemplo de ejecución:**

```python
# Escenario de falla:
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=5)

# Solicitud 1-5: SES falla por email no verificado
for i in range(5):
    try:
        circuit_breaker.call(send_email_via_ses, "ORDER-123", "test@mail.com")
    except Exception:
        print(f"Falla {i+1}: Circuit breaker failure_count = {circuit_breaker.failure_count}")

# Después de 5 fallas: circuit_breaker.state = "OPEN"
# Solicitud 6+: Todas bloqueadas inmediatamente
try:
    circuit_breaker.call(send_email_via_ses, "ORDER-124", "test@mail.com")
except Exception as e:
    print(f"Error: {e}")  # "Circuit breaker is OPEN - all requests blocked"
```

## **Soluciones propuestas:**

### **Solución Inmediata (Crítica):**

1. **Verificar emails en AWS SES:**
   ```bash
   aws ses verify-email-identity --email-address no-reply@example.com
   aws ses verify-email-identity --email-address test@mail.com
   ```

2. **Corregir la lógica del Circuit Breaker:**
   ```python
   def call(self, func, *args, **kwargs):
       if self.state == "OPEN":
           # CORRECCIÓN: Cambiar < por >=
           if time.time() >= self.last_failure_time + self.recovery_timeout:
               self.state = "HALF-OPEN"
               print("Transition to HALF-OPEN state.")
           else:
               raise Exception("Circuit breaker is OPEN - all requests blocked")
   ```

### **Soluciones de Configuración:**

3. **Configurar variable de entorno STATUS_CHECK_URL:**
   ```bash
   aws lambda update-function-configuration \
     --function-name EmailServiceFunction \
     --environment Variables={STATUS_CHECK_URL=https://httpbin.org/status/200,SENDER_EMAIL=verified-email@yourdomain.com}
   ```

4. **Implementar modo de recuperación manual:**
   ```python
   # Agregar endpoint para resetear circuit breaker
   def reset_circuit_breaker():
       global circuit_breaker
       circuit_breaker.state = "CLOSED"
       circuit_breaker.failure_count = 0
       circuit_breaker.last_failure_time = None
   ```

### **Soluciones a Largo Plazo:**

5. **Persistir estado del Circuit Breaker en DynamoDB** para evitar que se resetee con cada nueva instancia de Lambda.

6. **Implementar fallback de notificaciones:**
   ```python
   def send_notification_fallback(order_id, email):
       # Enviar a SQS/SNS como respaldo
       # O registrar en DynamoDB para procesamiento posterior
   ```

La aplicación está caída porque el circuit breaker se abre después de 5 fallas consecutivas de SES (por emails no verificados) y nunca se recupera debido a la lógica incorrecta de transición de estados.