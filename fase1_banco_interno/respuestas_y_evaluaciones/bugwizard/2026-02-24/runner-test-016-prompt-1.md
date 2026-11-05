## Análisis del Ticket de Soporte

**Ticket:** La aplicación de transferencias entre cuentas presenta bloqueos intermitentes donde las cuentas quedan bloqueadas y no pueden procesar nuevas transacciones.

## Hallazgos en los logs

Analizando los logs de CloudWatch, se identifican patrones críticos:

1. **Timeouts masivos**: Todas las funciones Lambda están alcanzando el timeout de 60 segundos configurado
   ```
   REPORT RequestId: f082765f-252b-4940-acf9-8b354f2d858b Duration: 60000.00 ms Billed Duration: 60000 ms Status: timeout
   ```

2. **Patrón de ejecución bloqueado**: Las transacciones llegan hasta la fase 2 (ATTEMPT) pero nunca completan:
   ```
   TXN: 7d51ed1d-509a-4853-addb-f04d9df017f8 | RES: A | PH: 2 | STATE: ATTEMPT
   ```

3. **Transacciones concurrentes**: Se observan múltiples transacciones ejecutándose simultáneamente entre las mismas cuentas A y B, creando condiciones de deadlock.

4. **Ausencia de estados finales**: No se encuentran logs de "STATE: FINISH" ni mensajes de error específicos, indicando que las funciones se cuelgan en algún punto.

## Relación con el código fuente

### Problema principal identificado en `transfer_funds.py`:

**Línea crítica problemática:**
```python
def verify_settlement_window(acc_id):
    try:
        with urllib.request.urlopen(PROCESSOR_URL, timeout=20) as response:
            return response.getcode() == 200
    except:
        return False
```

**Flujo de ejecución problemático:**
```python
reserve_resource(f"res:{source}", tx_id)  # Reserva recurso A
print(f"TXN: {tx_id} | RES: {source} | PH: 1 | STATE: RESERVED")

verify_settlement_window(source)  # AQUÍ SE CUELGA

print(f"TXN: {tx_id} | RES: {target} | PH: 2 | STATE: ATTEMPT")
reserve_resource(f"res:{target}", tx_id)  # Nunca llega aquí
```

### Problema en `resource_registry.py`:

**Bucle infinito sin timeout:**
```python
def reserve_resource(resource_key, tx_id):
    start = time.time()  # Variable no utilizada
    ttl = int(time.time()) + 300

    while True:  # BUCLE INFINITO SIN CONDICIÓN DE SALIDA
        try:
            table.put_item(...)
            return True
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            time.sleep(0.1)  # Espera indefinidamente
```

## Ejemplo de ejecución

**Escenario de deadlock:**

1. **Transacción A→B** reserva recurso A, llama a `verify_settlement_window()`
2. **Transacción B→A** reserva recurso B, llama a `verify_settlement_window()`
3. Ambas transacciones intentan reservar el segundo recurso pero están bloqueadas
4. El endpoint `PROCESSOR_URL` no responde o es lento
5. Las funciones Lambda alcanzan el timeout de 60 segundos
6. Los recursos quedan reservados en DynamoDB con TTL de 300 segundos

## Soluciones propuestas

### Solución 1: Corregir el bucle infinito en resource_registry.py
```python
def reserve_resource(resource_key, tx_id, max_wait_time=30):
    start = time.time()
    ttl = int(time.time()) + 300

    while time.time() - start < max_wait_time:
        try:
            table.put_item(
                Item={
                    'resource_key': resource_key,
                    'tx_id': tx_id,
                    'timestamp': Decimal(str(time.time())),
                    'ttl': ttl
                },
                ConditionExpression='attribute_not_exists(resource_key)'
            )
            return True
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            time.sleep(0.1)
    
    raise Exception(f"Could not reserve resource {resource_key} within {max_wait_time} seconds")
```

### Solución 2: Mejorar verify_settlement_window con timeout más corto
```python
def verify_settlement_window(acc_id):
    try:
        with urllib.request.urlopen(PROCESSOR_URL, timeout=5) as response:  # Reducir timeout
            return response.getcode() == 200
    except Exception as e:
        print(f"Settlement window check failed: {str(e)}")
        return False
```

### Solución 3: Implementar ordenamiento de recursos para evitar deadlocks
```python
def handler(event, context):
    data = json.loads(event.get('body', '{}'))
    source = data.get('from_account')
    target = data.get('to_account')
    tx_id = str(uuid.uuid4())

    # Ordenar recursos alfabéticamente para evitar deadlocks
    resources = sorted([f"res:{source}", f"res:{target}"])
    
    try:
        # Reservar recursos en orden consistente
        for resource in resources:
            reserve_resource(resource, tx_id)
            
        # Resto de la lógica...
```

### Solución 4: Mejorar manejo de errores y cleanup
```python
def handler(event, context):
    # ... código inicial ...
    reserved_resources = []
    
    try:
        # Lógica de reserva con tracking
        for resource in resources:
            reserve_resource(resource, tx_id)
            reserved_resources.append(resource)
            
        # ... resto de lógica ...
        
    except Exception as e:
        print(f"TXN: {tx_id} | ERROR: {type(e).__name__} | MSG: {str(e)}")
        # Cleanup garantizado
        for resource in reserved_resources:
            release_resource(resource, tx_id)
        return {"statusCode": 500, "body": "Service Unavailable"}
```

La causa raíz es la combinación de un bucle infinito en la reserva de recursos y la llamada bloqueante a un endpoint externo, creando condiciones perfectas para deadlocks y timeouts.