# condefects-runner — Runner source-only de BugWizard para ConDefects

Corre BugWizard headless sobre cada programa de ConDefects **sin usar la interfaz
web y sin CloudWatch/git**, y guarda la respuesta cruda para puntuarla con
`../condefects-eval/score.py`.

## Cómo funciona (por cada programa)

1. **Proyecto** (socket `projects`): crea un proyecto `NIVEL3` con
   `repositoryType=zip` subiendo un `repository.zip` que contiene **solo el
   archivo fallado** (`faultyVersion.py`), y `logType=['file']`.
   → No requiere credenciales de git ni CloudWatch.
2. **Conversación** (socket `conversations`): sube un archivo de log
   (`sin_logs.txt`, contenido "sin logs") con `allowEmptyLogIndex=true`.
3. **Análisis** (socket `messages`): envía el prompt y acumula el stream de la IA
   hasta `[[END_OF_MESSAGE]]`.
4. Guarda la respuesta en `PREDICTIONS_DIR/<program_key>.md`.

> ⚠️ El zip contiene únicamente `faultyVersion.py`. **Nunca** se suben
> `correctVersion.py` ni `faultLocation.txt` — eso filtraría la respuesta e
> invalidaría la evaluación.

## Requisitos

- Node 18+.
- Un **`BACKEND_TOKEN` (JWT) fresco** del backend de BugWizard. Es la única
  credencial necesaria (el token del runner viejo expiró).
- El dataset ConDefects clonado y el `manifest.csv` generado con
  `build_manifest.py`.

## Uso

```bash
cd condefects-runner
npm install

# 1) generar el manifiesto (desde condefects-eval/)
python3 ../condefects-eval/build_manifest.py -w ../ConDefects/Code -o ../condefects-eval/manifest.csv -l python

# 2) editar run.sh: pegar el BACKEND_TOKEN y ajustar rutas / LIMIT
#    (CHECKOUT_DIR debe ser el mismo dir usado en build_manifest.py)

# 3) correr
bash run.sh
```

Variables de entorno (ver `run.sh`):

| Variable | Descripción |
|---|---|
| `BACKEND_TOKEN` | JWT fresco (obligatorio) |
| `BACKEND_URL` / `BACKEND_WS_URL` | endpoints del backend |
| `CHECKOUT_DIR` | dir del checkout/Code de ConDefects (el mismo del manifiesto) |
| `MANIFEST` | ruta del `manifest.csv` |
| `PREDICTIONS_DIR` | dónde se guardan las `.md` (input de `score.py`) |
| `LIMIT` | nº máximo de programas (para pruebas chicas) |
| `LOG_TEXT` | contenido del log; por defecto `"sin logs"` |
| `LOGS_DIR` | carpeta con `<program_key>.log` por programa; si existe, tiene prioridad sobre `LOG_TEXT` |

El runner es **reanudable**: si ya existe `PREDICTIONS_DIR/<program_key>.md`, salta
ese programa. Además, al arrancar consulta `GET /projects` del backend y arma un
mapa `projectName -> projectId`; si una corrida anterior alcanzó a crear el
proyecto pero falló en un paso posterior (conversación/análisis), **reutiliza**
ese proyecto en vez de intentar crearlo de nuevo (el backend rechaza nombres de
proyecto duplicados por usuario con "Proyecto ya existe con el mismo nombre
para el usuario").

## Modo con síntoma (recomendado, mejor experimentalmente)

En vez de "sin logs", se puede subir un log real y específico por programa con
los casos de prueba que fallan (entrada, salida esperada, salida obtenida). Así
el archivo de log cumple el rol de especificación del comportamiento, más
parecido al uso real de BugWizard.

Dos formas:

- **Manual / igual para todos**: exportar `LOG_TEXT` con un texto fijo
  (`export LOG_TEXT="entrada:\n3 1 2\nesperado: 6\nobtenido: 0"`).
- **Automático / por programa (recomendado)**: generar un `.log` por programa
  con `../condefects-eval/generate_test_logs.py` (ejecuta el código fallado
  contra los test cases reales de ConDefects y arma un resumen OK/FAIL + el
  detalle de los casos fallidos) y apuntar `LOGS_DIR` a esa carpeta:

      python3 ../condefects-eval/generate_test_logs.py \
          --manifest ../condefects-eval/manifest_subset.csv \
          --checkout ../ConDefects/Code \
          --test-root ../testcondefects/Test \
          --out-dir ../condefects-eval/logs

      export LOGS_DIR="../condefects-eval/logs"

  Si existe `LOGS_DIR/<program_key>.log`, el runner sube ese archivo (con ese
  nombre) en vez de `LOG_TEXT`. Si no existe para un programa puntual, cae al
  `LOG_TEXT` genérico. Ya viene configurado por defecto en `run.sh`.

## Después de correr

```bash
python3 ../condefects-eval/score.py \
    -m ../condefects-eval/manifest.csv \
    -p ../condefects-eval/predictions \
    -o ../condefects-eval/report.csv --system bugwizard
```

## Notas de implementación

- Los campos `repositoryAccount/cloudwatchAccount/newRelicAccount` se envían como
  UUID nil (`00000000-...`) porque el DTO los exige pero el backend no los usa con
  `zip` + `file`. Si el backend rechazara la validación, revisar esos campos.
- Checksums: MD5 hex del **string base64** (igual que `calculateBase64Hash` del
  backend).
- Programas de ConDefects son diminutos → los archivos se suben en un solo chunk.
