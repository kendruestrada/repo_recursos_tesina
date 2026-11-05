# Fase 2: validación externa sobre ConDefects

Corresponde a la sección 4.3 y al Anexo C de la tesina.

[ConDefects](https://github.com/appmlk/ConDefects) reúne programas defectuosos de concursos de AtCoder.
Para cada uno indica la línea del defecto, la versión corregida y los casos de prueba. El dataset no se
incluye aquí, así que hay que clonarlo desde su repositorio.

## Contenido

| Ruta | Qué hay |
|---|---|
| `condefects-eval/manifest_subset36.csv` | Los 36 programas Python evaluados, con su línea defectuosa. |
| `condefects-eval/generate_test_logs.py` | Genera un log por programa ejecutando la versión defectuosa contra los casos de prueba y marcando cada caso como OK o FAIL. |
| `condefects-eval/logs/` | Los 36 logs generados, que se entregaron a todos los sistemas. |
| `condefects-eval/predictions*/` | Respuestas crudas de BugWizard (`predictions/`), Claude Code, Gemini CLI y Gemini API. |
| `condefects-eval/report_*_36.csv` | Puntaje por programa (hit@1, hit@3, hit@5). |
| `condefects-eval/score.py`, `adapter.py` | Extraen las líneas propuestas (por su texto exacto) y calculan Top-N. |
| `condefects-eval/run_cli_baseline.py` | Ejecuta Claude Code y Gemini CLI en modo headless. |
| `condefects-eval/run_gemini_api_baseline.py` | Ejecuta Gemini API directa, sin agente. |
| `condefects-runner/` | Ejecuta BugWizard (requiere una instancia del backend, que no es pública). |
| `condefects-eval/NOTAS_DE_TRABAJO.md` | Notas de desarrollo del pipeline. Mencionan corridas preliminares cuyos archivos no se incluyen. |

## Reproducir los puntajes

```bash
git clone https://github.com/appmlk/ConDefects.git
cd ConDefects && python3 ConDefects.py checkout -w ./Code -l python && cd ..

cd condefects-eval
python3 score.py -m manifest_subset36.csv -p predictions            --checkout ../ConDefects/Code -o r_bw.csv  --system bugwizard
python3 score.py -m manifest_subset36.csv -p predictions_claude_code --checkout ../ConDefects/Code -o r_cc.csv  --system claude-code
python3 score.py -m manifest_subset36.csv -p predictions_gemini_cli  --checkout ../ConDefects/Code -o r_gc.csv  --system gemini-cli
python3 score.py -m manifest_subset36.csv -p predictions_gemini_api  --checkout ../ConDefects/Code -o r_ga.csv  --system gemini-api
```

Resultado esperado (Tabla 8 de la tesina):

| Sistema | Top-1 | Top-3 |
|---|---|---|
| BugWizard | 77,78% | 83,33% |
| Claude Code | 69,44% | 75,00% |
| Gemini CLI | 83,33% | 86,11% |
| Gemini API | 66,67% | 72,22% |
