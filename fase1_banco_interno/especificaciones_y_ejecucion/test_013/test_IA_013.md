# Resumen de hallazgos

## Contexto

Servicio AWS SAM con una Lambda Python expuesta por API Gateway (`POST /process`), código en `app`.

## Hallazgos

### 1) Hallazgo 1 (crítico / despliegue-build)

En `template.yaml` el Runtime estaba configurado como `python3.13`. Ese runtime normalmente no está soportado por AWS Lambda/SAM, lo que puede provocar fallos en `sam validate`, `sam build` o en el despliegue del stack.

### 2) Hallazgo 2 (crítico / ejecución en producción)

En `app.py` la función obtiene una conexión del pool (`getconn()`), pero en el flujo exitoso no la devuelve (`putconn()`). Con invocaciones repetidas esto puede agotar el semáforo del pool y derivar en bloqueos/timeout o degradación progresiva del servicio.

## Acciones correctivas aplicadas

- Cambio de Runtime a `python3.12` en `template.yaml`.
- Liberación garantizada de la conexión con bloque `finally` en `app.py`, y robustez adicional para `body=None`.

## Impacto esperado

- Se elimina el riesgo de incompatibilidad de runtime en build/deploy.
- Se evita el agotamiento del pool y los timeouts intermitentes bajo carga.