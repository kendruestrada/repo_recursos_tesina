Con toda la información recopilada, tengo suficiente evidencia para el análisis completo.

---

## Connection Pool Starvation: Semaforo no liberado en el path exitoso

### Summary: La función Lambda agota el pool de conexiones tras 5 invocaciones exitosas porque `putconn()` nunca se llama en el flujo de éxito, bloqueando indefinidamente en `semaphore.acquire()` hasta el timeout de 30 segundos.

### Severity: Critical

---

### Root Cause Analysis

**Evidencia en logs**

- Fase exitosa: 2026-02-18 13:00 hasta ~2026-02-18 18:xx — duraciones de 1-95ms, funcionamiento normal.
- Fase de fallos: a partir de 2026-02-19, **215 timeouts** consecutivos, todos con exactamente `Duration: 30000.00 ms` — el Lambda alcanza el limite configurado en `template.yaml:13`.
- El patrón es determinístico, no aleatorio: ocurre exactamente después de consumir `maxconn=5` conexiones en un mismo contenedor.

**Flujo de ejecución roto**

`app.py` líneas 21-41:

```python
conn = connection_pool.getconn()   # ← semaphore.acquire() → count: 5→4→3→2→1→0

try:
    # ... procesamiento ...
    return {                        # ← RETORNA SIN LLAMAR putconn(conn)
        "statusCode": 200,
        "body": json.dumps(result)
    }

except Exception as e:
    connection_pool.putconn(conn)  # ← Solo se libera en excepción
    return { "statusCode": 500 ... }
```

`database.py` líneas 9-17:

```python
def getconn(self):
    self._semaphore.acquire()      # ← Bloqueo indefinido cuando count == 0
    self._conn_count += 1
    return {...}

def putconn(self, conn):
    if self._conn_count > 0:
        self._conn_count -= 1
        self._semaphore.release()  # ← Nunca se llama en path exitoso
```

**Ejemplo de ejecución hipotética (contenedor con maxconn=5)**

| Invocación | Semáforo antes | Resultado | Semáforo después | putconn llamado |
|---|---|---|---|---|
| 1 | 5 | 200 OK | 4 | NO |
| 2 | 4 | 200 OK | 3 | NO |
| 3 | 3 | 200 OK | 2 | NO |
| 4 | 2 | 200 OK | 1 | NO |
| 5 | 1 | 200 OK | 0 | NO |
| 6 | 0 | **BLOQUEO** → timeout 30s | 0 | — |

**Ubicacion del bug**

- `app/app.py:38` — `return` exitoso sin `connection_pool.putconn(conn)`
- `app/app.py:43-45` — `putconn` solo en el `except`, nunca en el `try` success path

**Por que parece "aleatorio"**: Lambda crea nuevos contenedores al escalar o tras terminaciones forzadas por timeout. Cada contenedor nuevo tiene semáforo fresco en 5, ejecuta exitosamente 5 requests, luego bloquea indefinidamente. El patrón aparece aleatorio porque los contenedores se reciclan en momentos distintos.

---

### Solution

El `putconn()` debe ejecutarse siempre, independientemente del resultado. Usar bloque `finally`:

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
        connection_pool.putconn(conn)   # ← Siempre libera, tanto en éxito como en error
```

Este cambio en `app/app.py:43-49` elimina el `putconn` del `except` y lo mueve al `finally`, garantizando que el semáforo se libere en cada invocación sin importar el resultado.

# Total cost USD

0.63637825

# Execution time in seconds: 

88
