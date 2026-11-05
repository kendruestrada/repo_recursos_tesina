## Análisis del Ticket de Soporte Técnico

**Ticket:** La aplicación funciona correctamente inicialmente, pero después de un tiempo comienza a experimentar timeouts aleatorios que afectan el rendimiento del sistema.

## Hallazgos en los logs

Tras analizar exhaustivamente los logs de CloudWatch, se identificaron patrones críticos:

### 1. **Patrón de Timeouts Sistemáticos**
- **Frecuencia:** Aproximadamente cada 4ta invocación termina en timeout
- **Duración:** Exactamente 30,000 ms (30 segundos) - límite máximo de timeout de Lambda
- **Estado:** `Status: timeout` en todos los casos problemáticos

### 2. **Ejemplos de Timeouts Detectados:**
```
RequestId: 9afe6ab5-12c5-416d-b54e-7d41d9b6f183
Duration: 30000.00 ms	Status: timeout

RequestId: c3e0d2b9-4942-4dcd-bb9e-86b57b68a20d  
Duration: 30000.00 ms	Status: timeout

RequestId: 4cb08125-6271-42ea-b987-84f3f3807c9b
Duration: 30000.00 ms	Status: timeout
```

### 3. **Invocaciones Exitosas vs Problemáticas**
- **Exitosas:** 1.5-3ms de duración promedio
- **Problemáticas:** 30,000ms (timeout completo)
- **Memoria:** Consistente en 38-39 MB (sin problemas de memoria)

## Relación con el código fuente

### **Problema Identificado: Resource Leak en Connection Pool**

En el archivo `bw_test_013/app/app.py`, líneas 21-44:

```python
def lambda_handler(event, context):
    request_id = getattr(context, 'aws_request_id', 'local-id')
    logger.info(f"START - Node:{CID} - Request:{request_id}")
    
    conn = connection_pool.getconn()  # ← CONEXIÓN OBTENIDA
    
    try:
        # ... procesamiento ...
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
        # ← CONEXIÓN NUNCA SE LIBERA EN CASO EXITOSO
        
    except Exception as e:
        logger.error(f"Execution error: {str(e)}")
        connection_pool.putconn(conn)  # ← SOLO SE LIBERA EN EXCEPCIÓN
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Processing Error"})
        }
```

### **Análisis del Connection Pool:**

En `bw_test_013/app/db/database.py`:

```python
class SimpleConnectionPool:
    def __init__(self, minconn, maxconn, database=None):
        self.maxconn = maxconn  # maxconn = 5
        self._semaphore = threading.Semaphore(maxconn)  # 5 conexiones máximo
        
    def getconn(self):
        self._semaphore.acquire()  # Bloquea si no hay conexiones disponibles
```

## Ejemplo de ejecución

**Simulación del problema:**

```
Invocación 1: getconn() → conexión 1 obtenida → éxito → conexión NO liberada
Invocación 2: getconn() → conexión 2 obtenida → éxito → conexión NO liberada  
Invocación 3: getconn() → conexión 3 obtenida → éxito → conexión NO liberada
Invocación 4: getconn() → conexión 4 obtenida → éxito → conexión NO liberada
Invocación 5: getconn() → conexión 5 obtenida → éxito → conexión NO liberada
Invocación 6: getconn() → BLOQUEO INDEFINIDO → TIMEOUT después de 30s
```

**Estado del semáforo:**
- Inicial: 5 permisos disponibles
- Después de 5 invocaciones exitosas: 0 permisos disponibles
- Invocación 6+: `_semaphore.acquire()` bloquea indefinidamente

## Soluciones propuestas

### **Solución 1: Implementar finally block (Recomendada)**

```python
def lambda_handler(event, context):
    request_id = getattr(context, 'aws_request_id', 'local-id')
    logger.info(f"START - Node:{CID} - Request:{request_id}")
    
    conn = connection_pool.getconn()
    
    try:
        body_raw = event.get("body") if event else "{}"
        if isinstance(body_raw, str):
            body = json.loads(body_raw)
        else:
            body = body_raw
            
        result = {
            "status": "success",
            "data": {
                "id": body.get("id", "0"),
                "node_ref": CID
            }
        }

        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Execution error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Processing Error"})
        }
    finally:
        # CRÍTICO: Siempre liberar la conexión
        connection_pool.putconn(conn)
```

### **Solución 2: Context Manager**

```python
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = connection_pool.getconn()
    try:
        yield conn
    finally:
        connection_pool.putconn(conn)

def lambda_handler(event, context):
    request_id = getattr(context, 'aws_request_id', 'local-id')
    logger.info(f"START - Node:{CID} - Request:{request_id}")
    
    with get_db_connection() as conn:
        # ... resto del código ...
```

### **Solución 3: Mejorar el Connection Pool con timeout**

```python
def getconn(self, timeout=5):
    if self._semaphore.acquire(timeout=timeout):
        self._conn_count += 1
        return {"id": f"db_conn_{id(self)}_{self._conn_count}", "status": "active"}
    else:
        raise Exception("No database connections available")
```

**Causa raíz:** Resource leak en el connection pool debido a conexiones no liberadas en ejecuciones exitosas, causando agotamiento del pool y bloqueos indefinidos en invocaciones posteriores.