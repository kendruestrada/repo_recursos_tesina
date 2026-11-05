# Fase 1: banco interno con evaluación ciega

Corresponde a la sección 4.2 de la tesina.

## Contenido

| Carpeta | Qué hay |
|---|---|
| `escenarios/bw_test_0XX/` | Código e infraestructura (SAM/CDK) de cada escenario sintético: aplicaciones serverless en AWS con un defecto inyectado. Los escenarios 001 a 003 no tienen el código disponible. |
| `especificaciones_y_ejecucion/test_0XX/` | Especificación de cada escenario: síntoma, flujo del error, **causa raíz** y las preguntas usadas como prompt. |
| `especificaciones_y_ejecucion/synthetics-canaries/` | Proyecto CDK de CloudWatch Synthetics que ejercita los escenarios para generar tráfico y logs. |
| `especificaciones_y_ejecucion/llm-testing-scripts/` | Scripts que ejecutaron Claude Code y Gemini CLI (`run-tests.sh`), con la definición de las tres configuraciones en `projects.json` y el prompt de sistema. |
| `bugwizard-runner/` | Cliente que ejecutó BugWizard sobre cada escenario (requiere una instancia del backend, que no es pública). |
| `respuestas_y_evaluaciones/` | Respuestas originales de cada agente (`bugwizard/`, `claude/`, `gemini/`), las versiones anonimizadas y desordenadas que vieron los jueces (`Test-revisados/`) y las notas de los dos expertos (`Notas/`). |
| `analisis/` | `oe2_analisis.py` y sus salidas: datos brutos (288 calificaciones), medias, Wilcoxon y reporte. |
| `incidentes_reales/` | Calificaciones de los 10 incidentes reales (160 evaluaciones). Solo se incluyen los títulos de los incidentes, porque el material de los clientes es confidencial. |

## Las ocho configuraciones

En `projects.json` cada escenario define tres pruebas para Claude Code y Gemini CLI:

| Prueba | En la tesina | Qué recibe |
|---|---|---|
| `source-only` | solo código | Repositorio e instrucción genérica, sin logs (`cw-mcp: false`). |
| `source-and-logs` | código + logs | Repositorio, síntoma y acceso a CloudWatch mediante el servidor MCP *Log Analyzer with MCP* (`cw-mcp: true`). |
| `detailed-source-and-logs` | detallado | Lo mismo, más el relato del flujo esperado. |

BugWizard se ejecutó con dos prompts: *prompt 1* (síntoma) y *prompt 2* (síntoma y relato). En ambos casos
usó RAG de una sola llamada, con el código y los logs indexados al crear la conversación.

## Reproducir el análisis

```bash
pip install pandas numpy
python3 analisis/oe2_analisis.py
```

Regenera los archivos de `analisis/`. Las medias deben coincidir con la Tabla 5 de la tesina.
