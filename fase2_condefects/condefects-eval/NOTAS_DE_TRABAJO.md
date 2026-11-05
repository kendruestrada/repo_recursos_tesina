# Evaluación de BugWizard sobre ConDefects (fault localization, Top-N)

## Actualización a Claude Sonnet 5 (septiembre 2026)

Se repitieron las corridas de BugWizard y Claude Code con **Claude Sonnet 5**
(`arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.anthropic.claude-sonnet-5`,
vía Bedrock, perfil AWS `DevRole-123456789012`), mismo subconjunto
(`manifest_subset36.csv`), mismos logs (`logs/`) y mismo prompt. Las corridas
de Gemini no dependen del modelo de Claude y no se repitieron.

| Sistema (n=36)          | Top-1           | Top-3/5         |
| ----------------------- | --------------- | --------------- |
| BugWizard — Sonnet 4    | 61.11% (22)     | 72.22% (26)     |
| BugWizard — Sonnet 5    | **77.78% (28)** | **83.33% (30)** |
| Claude Code — Sonnet 4  | 58.33% (21)     | 72.22% (26)     |
| Claude Code — Sonnet 5  | **69.44% (25)** | **75.00% (27)** |

Cambios por programa en Top-1 (Sonnet 4 → 5): BugWizard 8 mejoran / 2
empeoran (`abc243_e`, `abc289_h`); Claude Code 4 mejoran / 0 empeoran. Con
n=36 ninguna diferencia es significativa por McNemar exacto (p≈0.11 y
p≈0.125): reportar como tendencia.

Archivos:
- Sonnet 5: `predictions/`, `predictions_claude_code/`,
  `report_bugwizard_36.csv`, `report_claude-code_36.csv`.
- Sonnet 4 (respaldo): `predictions_sonnet4_bugwizard/`,
  `predictions_sonnet4_claude_code/`, `report_bugwizard_36_sonnet4.csv`,
  `report_claude-code_36_sonnet4.csv`.
- `report_bugwizard_35_sonnet4_original.csv` es el reporte original de
  Sonnet 4, puntuado cuando faltaba la predicción de `abc333_a` (de ahí el
  60.00%/71.43% sobre n=35 de más abajo). `report_bugwizard_36_sonnet4.csv`
  es el re-puntaje sobre las 36 predicciones, que es el comparable.

Diferencias de condiciones a declarar:
- **Thinking:** Sonnet 5 usa *adaptive thinking* por defecto. En BugWizard
  está activo; en Claude Code, pese a `MAX_THINKING_TOKENS=0`, los tiempos
  (3 programas >180 s) indican que también razona. Con Sonnet 4 ninguno
  razonaba, así que parte de la mejora puede venir del thinking y no solo
  del modelo base.
- **Timeout de Claude Code:** `abc245_h`, `abc275_g` y `abc328_e` excedieron
  180 s y se re-corrieron con `--timeout 600`.
- **Backend de BugWizard:** con `max_tokens=4000` Sonnet 5 agotaba el
  presupuesto pensando y devolvía texto vacío (`stop_reason=max_tokens` →
  "Message content cannot be empty"). Se subió a `max_tokens=32000`
  (`ms-agente-tickets`, rama `feature/sonnet-5-max-tokens`) antes de correr.
  El runner ahora corta cada análisis a los 10 min (`ANALYSIS_TIMEOUT_MS`)
  porque el backend no emite `[[ERROR_MESSAGE]]` en ese caso.

La sección "Modelo — importante para la comparación justa" de más abajo
describe la configuración original con Sonnet 4.

## Cambio de metodología: texto de línea en vez de número (importante)

Las primeras corridas (`predictions_v1_numeric_*`, `report_v1_numeric_*`) le
pedían al sistema el **número** de línea directamente. Eso resultó injusto
para BugWizard: arma el contexto vía RAG (indexa y recupera código/logs), lo
que no garantiza numeración verbatim del archivo original — revisando las
transcripciones reales, su diagnóstico semántico era correcto en los 3 casos
que "falló", pero el número de línea reportado estaba sistemáticamente corrido
(atribuía el bug a la línea `if`/`else` de al lado en vez de a la sentencia
exacta que su propia explicación señalaba).

Desde ahora el contrato pide el **texto exacto** de la línea
(`LINEAS_FALLA_TEXTO:`, ver `run_cli_baseline.py` y
`condefects-runner/src/index.ts`), y `adapter.resolve_line_numbers` lo busca
en el archivo fuente real para obtener el número — así la métrica mide
"¿encontró el bug?" y no "¿supo contar líneas?". `score.py` necesita
`--checkout <dir>` para poder abrir el archivo fuente y resolver el texto; sin
ese flag, solo reconoce el contrato viejo (compatibilidad).

Los reportes/predicciones `_v1_numeric_*` se conservan como referencia de la
metodología anterior. Para comparar con el contrato nuevo, hay que **volver a
correr** BugWizard y Claude Code (los directorios `predictions/` y
`predictions_claude_code/` ya se vaciaron) y puntuar con:

```bash
python3 score.py -m manifest_subset.csv -p predictions            --checkout ../ConDefects/Code -o report_bugwizard.csv   --system bugwizard
python3 score.py -m manifest_subset.csv -p predictions_claude_code --checkout ../ConDefects/Code -o report_claude_code.csv --system claude-code
```


Pipeline mínimo para evaluar la capacidad de **localización de fallas a nivel de
línea** de BugWizard usando el dataset público **ConDefects**
(https://github.com/appmlk/ConDefects), y compararlo con baselines (SBFL Ochiai
del propio toolkit, y otros LLMs).

Es una evaluación **source-only**: se le entrega a BugWizard el código fallado y
un archivo de log "sin logs"; no ejercita la mitad de observabilidad del agente.
Es la limitación a declarar en la tesina.

## Formato del ground truth (confirmado desde el toolkit)

Tras `python3 ConDefects.py checkout -w <dest> -l python`, cada programa queda en:

    <dest>/<task>/<language>/<programID>/
        faultyVersion.py      # código con el bug
        correctVersion.py     # versión corregida
        faultLocation.txt     # entero: línea 1-based de la falla

- `task` = `<contest>_<letra>` (ej. `abc217_a`).
- `faultLocation.txt` contiene la línea gold **1-based** (así lo usa `Tool/Info.py`,
  que hace `int(faultLocation) - 1` para indexar `readlines()`).
- Los casos de prueba (`Test/`) solo se necesitan para el baseline SBFL o para
  darle a BugWizard un test que falla como "síntoma"; NO son necesarios para
  puntuar la localización.

## Componentes

- `build_manifest.py` — recorre un checkout de ConDefects y arma `manifest.csv`
  (una fila por programa: `program_key`, `gold_lines`, ruta, etc.).
- `adapter.py` — extrae de la salida markdown de BugWizard la lista **ordenada**
  de líneas predichas. Contrato recomendado del prompt: terminar con
  `ARCHIVO: ...` / `LINEAS_FALLA: [12, 5, 30]`. Si no está el bloque, cae a
  heurísticas sobre texto libre ("línea 12", "line 12", "L12").
- `score.py` — compara predicciones vs gold y reporta **Top-1/3/5**.
  `hit@N = 1` si alguna línea gold está entre las primeras N predichas.

## Flujo de uso (en tu máquina, donde git funciona)

1. Clonar y preparar ConDefects:

       git clone https://github.com/appmlk/ConDefects.git
       cd ConDefects
       # colocar Test.zip (OneDrive/Baidu) junto a ConDefects.py si se usará SBFL

2. Checkout de una muestra Python (ej. ventana reciente para reforzar
   anti-leakage):

       python3 ConDefects.py checkout -w ./muestra -l python -t 2023-01-01 2023-09-30

3. Construir el manifiesto:

       python3 build_manifest.py -w ./muestra -o manifest.csv -l python

4. Correr BugWizard (nuevo runner source-only) sobre cada programa y guardar la
   salida cruda como `predictions/<program_key>.md` (mismo `program_key` del
   manifiesto).

5. Puntuar:

       python3 score.py -m manifest.csv -p predictions/ --checkout <checkout_dir> -o report.csv --system bugwizard

   Para comparar otro sistema, repetir con otra carpeta de predicciones y
   `--system <nombre>`.

## Contrato de salida para el prompt de BugWizard

Pedir explícitamente que la respuesta **termine** con (ver "Cambio de
metodología" más arriba sobre por qué texto y no número):

    ARCHIVO: faultyVersion.py
    LINEAS_FALLA_TEXTO:
    1. "<texto EXACTO de la línea más probable, tal como aparece en el archivo>"
    2. "<texto EXACTO de la segunda línea más probable>"
    3. "<texto EXACTO de la tercera línea más probable>"

La lista debe ir ordenada por confianza (más probable primero) para que Top-N
sea significativo. El adaptador es tolerante (cae al contrato viejo con
números si un sistema lo ignora), pero el bloque estructurado con texto exacto
es lo que da resultados limpios y no penaliza contar líneas mal.

## Fixture de prueba

`fixture/` reproduce el layout real con 3 programas y predicciones de ejemplo
(incluyendo un caso sin bloque estructurado). Sirve para validar los scripts sin
descargar el dataset completo:

    python3 build_manifest.py -w fixture/checkout -o out/manifest.csv -l python
    python3 score.py -m out/manifest.csv -p fixture/predictions -o out/report.csv --system bugwizard

Resultado esperado: Top-1 33.33%, Top-3 66.67%, Top-5 100%.

## Comparar contra Claude Code y Gemini CLI (`run_cli_baseline.py`)

Para poner a BugWizard junto a otros dos sistemas (Claude Code y Gemini CLI) en
la misma tarea de localización de fallas, `run_cli_baseline.py` corre esos CLIs
en modo headless sobre el mismo subconjunto y con el mismo prompt + log "con
síntoma" que recibe BugWizard, y guarda la respuesta en el mismo formato
`predictions_<sistema>/<program_key>.md` que ya consume `score.py`.

Condiciones iguales para los 3 sistemas: solo se copia `faultyVersion.py` a un
directorio temporal vacío (nunca `correctVersion.py` ni `faultLocation.txt`),
mismo prompt (pide el bloque `ARCHIVO:`/`LINEAS_FALLA:`), mismo log real de
`generate_test_logs.py`, y herramientas restringidas a solo-lectura.

### Modelo — importante para la comparación justa

BugWizard usa `anthropic.claude-sonnet-4-20250514-v1:0` vía **AWS Bedrock**
(confirmado en los scripts de deploy de `ms-agente-tickets` y `ms-log-monitor`).
Ese snapshot está **retirado en la API directa de Anthropic desde el
15/06/2026** (ver [Model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations)),
pero Bedrock tiene su propio calendario de retiro y BugWizard lo sigue usando
ahí activamente. Para que Claude Code use el **mismo modelo exacto** (no una
versión más nueva, que le daría ventaja), hay que correrlo también contra
Bedrock, apuntando al mismo inference profile:

```bash
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_PROFILE=DevRole-123456789012   # perfil con acceso al mismo Bedrock que usa BugWizard
export AWS_REGION=us-east-1

python3 run_cli_baseline.py --agent claude \
    --model 'arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0' \
    --manifest manifest_subset.csv --checkout ../ConDefects/Code \
    --logs-dir logs --predictions-dir predictions_claude_code
```

Si no tienes ese acceso AWS, la alternativa es usar el modelo activo más
cercano en la API directa (`--model claude-sonnet-4-5-20250929`) y documentar
la diferencia de modelo como limitación conocida del experimento.

**Setup previo obligatorio: bloquear WebSearch/WebFetch.** Gemini CLI tiene
acceso a `google_web_search`/`web_fetch` en modo headless y a veces decide
usarlas (probablemente para buscar el enunciado del problema); si el backend
de esa herramienta responde error 500 (visto en la práctica), el CLI entra en
un loop de reintentos con backoff que consume todo el `--timeout` sin nunca
generar la predicción. Se bloquea con el motor de políticas
(https://geminicli.com/docs/reference/policy-engine/), que además hace la
comparación más justa (Claude Code ya está restringido a `--tools Read`):

```bash
mkdir -p ~/.gemini/policies
cat > ~/.gemini/policies/no-web.toml <<'TOML'
[[rule]]
toolName = ["google_web_search", "web_fetch"]
decision = "deny"
priority = 100
denyMessage = "Deshabilitado para esta evaluacion: es una tarea source-only, no debe buscar en la web."
TOML
```

```bash
python3 run_cli_baseline.py --agent gemini --model gemini-2.5-flash \
    --manifest manifest_subset36.csv --checkout ../ConDefects/Code \
    --logs-dir logs --predictions-dir predictions_gemini_cli \
    --timeout 420
```

⚠️ Google anunció que Gemini CLI sería reemplazado por **Antigravity CLI** para
cuentas gratuitas/Google One a mediados de 2026. Verifica con `gemini --version`
que sigues teniendo el Gemini CLI clásico antes de correr esto — si tu cuenta
ya migró, los flags de este script (`-p`, `--model`, `--approval-mode`) pueden
no aplicar a Antigravity CLI y habría que revisar su documentación.

**Elección deliberada de modelo: `gemini-2.5-flash`, no Pro.** A diferencia de
Claude Code (Sonnet 4, mismo modelo que BugWizard), para Gemini se eligió
intencionalmente un modelo más débil/barato (`flash` en vez de `pro`) como
tercer punto de comparación — para ver cómo cae la localización de fallas con
un modelo de menor capacidad, no para igualar a BugWizard. Esto es una
decisión metodológica, no una limitación por cuota: declarar en la tesina que
Gemini CLI corrió con un modelo deliberadamente inferior al de los otros dos
sistemas.

**Requisito técnico: billing (Tier 1) habilitado.** El nivel gratuito de la
API (`generativelanguage.googleapis.com`) tiene **cuota 0** para
`gemini-2.5-pro` desde el recorte de Google del 7/12/2025. El problema es que
Gemini CLI hace llamadas internas de "utilidad" (clasificación, autocompletado)
que caen en cascada a `flash-lite` → `flash` → `pro` **sin respetar el
`--model` configurado** (comportamiento documentado en
https://geminicli.com/docs/cli/model-routing/) — así que aunque se pida
`flash` explícitamente, esas llamadas ocultas terminan golpeando la cuota 0 de
`pro` y cortan la corrida a medio camino. Con billing (Tier 1) habilitado esa
cuota 0 desaparece (deja de ser gratis, pero ya no es 0), así que el fallback
oculto a `pro` deja de romper la ejecución. Pasos para habilitar:

1. Ir a https://ai.google.dev/gemini-api/docs/billing (o directo a
   https://aistudio.google.com/billing) y vincular una cuenta de billing de
   Google Cloud al mismo proyecto de la API key usada por `gemini`.
2. La actualización a Tier 1 suele ser instantánea; se puede confirmar en
   https://aistudio.google.com/projects o en la página de rate limits
   (https://aistudio.google.com/rate-limit).
3. Correr el comando de arriba (`--model gemini-2.5-flash`) — el script es
   reanudable, así que solo reintenta los programas que aún no tienen `.md`
   en `predictions_gemini_cli/`.

### Cuarto sistema: Gemini vía API directa, sin agente (`run_gemini_api_baseline.py`)

Con WebSearch bloqueado, Gemini CLI + `gemini-2.5-flash` (el modelo
deliberadamente más débil) igual sacó Top-1 83% — más alto que BugWizard
(60%) y Claude Code (58%), lo cual es contraintuitivo dado que se supone que
es el modelo más débil. Antes de aceptar ese resultado hay que descartar una
explicación alternativa: Gemini CLI corre con su loop de agente completo
(thinking dinámico activado, tools de lectura/grep/glob disponibles,
clasificación interna) mientras que Claude Code se corrió deliberadamente
pelado (`--tools Read`, `MAX_THINKING_TOKENS=0`). Es decir, la comparación
puede estar midiendo "cuánto trabaja el agente" más que "qué tan bueno es el
modelo".

`run_gemini_api_baseline.py` aísla esa variable: llama **directo** a la API
REST de Google (`generateContent`), sin CLI, sin herramientas, con el código
fuente y el log pegados como texto plano en el prompt (nada de tool-use), y
con `thinkingBudget=0` (thinking apagado explícitamente — ver
https://ai.google.dev/gemini-api/docs/generate-content/thinking, tabla
"Thinking budgets": `gemini-2.5-flash` soporta `thinkingBudget=0` para apagar
completamente el razonamiento extendido). Es la versión "pelada" de Gemini,
tan comparable a Claude Code como es posible.

```bash
export GEMINI_API_KEY=...   # el mismo que ya usas con gemini-cli
python3 run_gemini_api_baseline.py --model gemini-2.5-flash \
    --manifest manifest_subset36.csv --checkout ../ConDefects/Code \
    --logs-dir logs --predictions-dir predictions_gemini_api
```

**Resultado (confirma la sospecha):**

| Sistema                              | Top-1  | Top-3/5 |
| ------------------------------------ | ------ | ------- |
| BugWizard                            | 60.00% | 71.43%  |
| Claude Code (`--tools Read`, sin thinking) | 58.33% | 72.22%  |
| Gemini CLI (agente completo, thinking on) | 83.33% | 86.11%  |
| Gemini API directa (sin agente, sin thinking) | 66.67% | 72.22%  |

Al sacarle el scaffolding de agente a Gemini (thinking apagado, sin
herramientas, una sola llamada), el Top-1 cae de 83.33% a 66.67% — casi 17
puntos — y queda en línea con Claude Code/BugWizard en vez de muy por encima.
Confirma que el resultado alto de Gemini CLI no reflejaba que el modelo
"débil" fuera mejor per se, sino que el agente completo (thinking dinámico +
herramientas de lectura/grep + iteración) hacía más trabajo de diagnóstico
del que se le permitió hacer a Claude Code. Conclusión para la tesina: el
scaffolding del agente (no solo el modelo base) es una variable relevante en
esta tarea, al menos en esta muestra (n=36).

### Puntuar cada sistema

```bash
python3 score.py -m manifest_subset36.csv -p predictions            --checkout ../ConDefects/Code -o report_bugwizard.csv   --system bugwizard
python3 score.py -m manifest_subset36.csv -p predictions_claude_code --checkout ../ConDefects/Code -o report_claude_code.csv --system claude-code
python3 score.py -m manifest_subset36.csv -p predictions_gemini_cli  --checkout ../ConDefects/Code -o report_gemini_cli.csv  --system gemini-cli
python3 score.py -m manifest_subset36.csv -p predictions_gemini_api  --checkout ../ConDefects/Code -o report_gemini_api.csv  --system gemini-api
```

El runner es reanudable (salta `<program_key>.md` ya generados) y no guarda
como predicción los errores del CLI (p. ej. "Not logged in"), aunque el CLI
los devuelva con código de salida distinto de cero y algo de texto en stdout.

## Runner (implementado)

El runner source-only ya está implementado en `../condefects-runner` (ver su
README): crea el proyecto NIVEL3 vía sockets, sube el log y captura la
respuesta de BugWizard como `predictions/<program_key>.md`.

## Logs de prueba con síntoma real (`generate_test_logs.py`)

En vez de subir "sin logs" (modo puro source-only) o un `LOG_TEXT` genérico
fijo, `generate_test_logs.py` genera un log **real y específico por programa**
ejecutando `faultyVersion.py` contra los test cases reales de ConDefects
(extraídos de `Test.zip` en `../testcondefects/Test`) y comparando la salida
obtenida contra la esperada.

Cada log incluye:
- un resumen `[OK]`/`[FAIL]` de todos los test cases del programa,
- el detalle completo (entrada/esperado/obtenido) de hasta 3 casos **fallidos**,
- un caso **exitoso** de referencia,

manteniendo el archivo corto (unos cientos de bytes) para no gastar tokens de
más, pero con la información mínima necesaria para que BugWizard entienda el
problema.

Uso:

    python3 generate_test_logs.py \
        --manifest manifest_subset.csv \
        --checkout ../ConDefects/Code \
        --test-root ../testcondefects/Test \
        --out-dir logs \
        --timeout 5

`manifest_subset.csv` es un recorte de `manifest.csv` (mismas columnas) con
solo los programas que se quieren probar — así se controla el tamaño/costo del
experimento. Ya incluye un subconjunto de ejemplo de 6 programas Python (tarea
`_a`, pocos test cases, ejecutan rápido) cuyos logs están en `logs/`.

`../condefects-runner` recoge automáticamente estos logs si se exporta
`LOGS_DIR=../condefects-eval/logs` (ya configurado en `run.sh`): si existe
`<program_key>.log`, se sube ese contenido; si no, cae al `LOG_TEXT` genérico.
