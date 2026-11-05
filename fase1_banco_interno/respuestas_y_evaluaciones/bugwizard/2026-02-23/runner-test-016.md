## Análisis del Ticket de Soporte

**Ticket:** La aplicación de transferencias entre cuentas presenta bloqueos intermitentes donde las cuentas quedan bloqueadas y no pueden procesar nuevas transacciones.

## Hallazgos en los logs

Analizando los logs de CloudWatch, se identifican patrones críticos:

1. **Timeouts masivos**: Todas las ejecuciones terminan con `Status: timeout` después de 60 segundos (60000.00 ms)
2. **Patrón de deadlock**: Se observan transacciones simultáneas que intentan reservar los mismos recursos en orden inverso:
   ```
   TXN: be83799e-26cb-443c-81a8-c87d4fc0f7d6 | SRC: A | DST: B | STATE: START
   TXN: 6a9bb126-416e-4e38-891c-17d4b90daf49 | SRC: B | DST: A | STATE: START
   ```
3. **Bloqueo en fase de reserva**: Las transacciones llegan hasta `STATE: ATTEMPT` pero nunca alcanzan `STATE: FINISH`
4. **Recursos nunca liberados**: No se observan logs de liberación exitosa de recursos

## Relación con el código fuente

### Problema principal en `resource_registry.py`:

```python
def reserve_resource(resource_key, tx_id):
    start = time.time()
    ttl = int(time.time()) + 300

    while True:  # ← BUCLE INFINITO SIN TIMEOUT
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
            time.sleep(0.1)  # ← Espera indefinida
```

### Problema en `transfer_funds.py`:

```python
def handler(event, context):
    # ...
    try:
        reserve_resource(f"res:{source}", tx_id)  # Reserva recurso A
        print(f"TXN: {tx_id} | RES: {source} | PH: 1 | STATE: RESERVED")

        verify_settlement_window(source)

        print(f"TXN: {tx_id} | RES: {target} | PH: 2 | STATE: ATTEMPT")
        reserve_resource(f"res:{target}", tx_id)  # Intenta reservar recurso B
        # ← Si falla aquí, nunca libera el recurso A
```

## Ejemplo de ejecución del deadlock

**Escenario:**
- Transacción T1: A → B (reserva A, luego intenta reservar B)
- Transacción T2: B → A (reserva B, luego intenta reservar A)

**Flujo de ejecución:**
```
T1: reserve_resource("res:A", "tx1") → SUCCESS
T2: reserve_resource("res:B", "tx2") → SUCCESS
T1: reserve_resource("res:B", "tx1") → BLOCKED (B ocupado por T2)
T2: reserve_resource("res:A", "tx2") → BLOCKED (A ocupado por T1)
```

**Resultado:** Ambas transacciones quedan en bucle infinito esperando recursos que nunca se liberarán.

## Soluciones propuestas

### Solución 1: Implementar timeout en reserve_resource

```python
def reserve_resource(resource_key, tx_id, timeout=30):
    start = time.time()
    ttl = int(time.time()) + 300

    while time.time() - start < timeout:
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
    
    raise Exception(f"Timeout waiting for resource {resource_key}")
```

### Solución 2: Ordenamiento de recursos para prevenir deadlocks

```python
def handler(event, context):
    # ...
    # Ordenar recursos alfabéticamente para evitar deadlocks
    resources = sorted([f"res:{source}", f"res:{target}"])
    
    try:
        # Reservar recursos en orden consistente
        for resource in resources:
            reserve_resource(resource, tx_id)
            print(f"TXN: {tx_id} | RES: {resource} | STATE: RESERVED")
        
        verify_settlement_window(source)
        
        # Liberar recursos
        for resource in resources:
            release_resource(resource, tx_id)
        
        print(f"TXN: {tx_id} | STATE: FINISH")
        return {"statusCode": 200, "body": json.dumps({"status": "ok", "trace": tx_id})}
        
    except Exception as e:
        # Liberar todos los recursos en caso de error
        for resource in resources:
            release_resource(resource, tx_id)
        raise e
```

### Solución 3: Implementar TTL automático en DynamoDB

Modificar el template.yaml para agregar TTL automático:

```yaml
TransactionTrackerTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: test-016-transaction-tracker
    AttributeDefinitions:
      - AttributeName: resource_key
        AttributeType: S
    KeySchema:
      - AttributeName: resource_key
        KeyType: HASH
    TimeToLiveSpecification:
      AttributeName: ttl
      Enabled: true
```

**Causa raíz:** El sistema presenta un deadlock clásico causado por la reserva de recursos en orden inconsistente combinado con un mecanismo de espera sin timeout, resultando en bloqueos indefinidos que agotan el tiempo de ejecución de Lambda.