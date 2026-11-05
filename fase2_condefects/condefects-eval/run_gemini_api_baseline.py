#!/usr/bin/env python3
"""
run_gemini_api_baseline.py — Corre gemini-2.5-flash llamando DIRECTO a la API
REST de Google (generateContent), sin pasar por Gemini CLI, sin agente, sin
herramientas, y con el "thinking" explícitamente apagado (thinkingBudget=0).

Por qué existe este script (además de run_cli_baseline.py --agent gemini):
Gemini CLI, aunque se le pida un modelo débil (flash) y se le bloquee
WebSearch, sigue corriendo con su loop de agente completo: thinking activado
por defecto, tools de lectura/grep/glob disponibles, clasificación interna,
etc. Eso mezcla "qué tan bueno es el modelo" con "cuánto trabajo extra hace el
agente por su cuenta" — y Claude Code, en cambio, se corrió deliberadamente
pelado (--tools Read, MAX_THINKING_TOKENS=0, ver run_cli_baseline.py). Si
Gemini vía CLI saca mejor puntaje que Claude Code/BugWizard pese a ser
"el modelo más débil", hay que descartar que sea el scaffolding del agente
(más pasos, más tiempo, más iteración) el que está inflando el resultado y no
el modelo en sí.

Este script hace la comparación más parecida posible a como corre Claude
Code: una sola llamada, sin herramientas, sin razonamiento extendido, con el
código fuente y el log pegados como texto plano en el prompt (nada de
tool-use ni file-attachment vía agente).

Uso:
    export GEMINI_API_KEY=...   # el mismo que ya usas con gemini-cli
    python3 run_gemini_api_baseline.py \
        --model gemini-2.5-flash \
        --manifest manifest_subset36.csv --checkout ../ConDefects/Code \
        --logs-dir logs --predictions-dir predictions_gemini_api

Luego puntuar igual que los demás:
    python3 score.py -m manifest_subset36.csv -p predictions_gemini_api \
        --checkout ../ConDefects/Code -o report_gemini_api_36.csv --system gemini-api
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Debe ser IDÉNTICO al de run_cli_baseline.py / condefects-runner/src/index.ts
# para que la comparación sea justa entre los 4 sistemas.
DEFAULT_PROMPT = """Analiza el código fuente adjunto e identifica la línea que contiene el bug.
Es un programa corto de programación competitiva.
Termina tu respuesta OBLIGATORIAMENTE con un bloque en este formato exacto:

ARCHIVO: <nombre_del_archivo>
LINEAS_FALLA_TEXTO:
1. "<texto EXACTO de la línea más probable, tal como aparece en el archivo>"
2. "<texto EXACTO de la segunda línea más probable>"
3. "<texto EXACTO de la tercera línea más probable>"

No indiques el número de línea: copia el TEXTO EXACTO de cada línea (mismo
contenido y espacios/indentación, sin agregar comentarios ni parafrasear).
Ordena de MÁS a MENOS probable."""


def build_prompt(source_filename: str, source_text: str, log_text: str | None) -> str:
    parts = [
        DEFAULT_PROMPT,
        "",
        f"El archivo de código a analizar es {source_filename}:",
        "```python",
        source_text.rstrip("\n"),
        "```",
        "",
        "Log de ejecución disponible (casos de prueba exitosos y fallidos reales):",
        "---",
        (log_text.strip() if log_text else "sin logs"),
        "---",
    ]
    return "\n".join(parts)


# Candidatos de fallback si el modelo pedido devuelve 404 "no longer
# available to new users" (política de Google: algunos modelos "legacy"
# siguen andando para cuentas viejas pero no se pueden empezar a usar desde
# proyectos/API keys nuevos). Se prueban en orden y se usa el primero que
# responda bien; se imprime cuál quedó para dejarlo documentado.
FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-preview-09-2025",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
]


def resolve_model(requested_model: str, api_key: str, timeout: float) -> str:
    """Prueba requested_model con una llamada minima; si da 404 'no longer
    available', prueba la lista de fallback en orden y devuelve el primero
    que funcione. Lanza si ninguno funciona."""
    candidates = [requested_model] + [m for m in FALLBACK_MODELS if m != requested_model]
    errors = []
    for model in candidates:
        try:
            call_gemini(model, "Reply with exactly: OK", api_key, timeout, thinking_budget=0)
            if model != requested_model:
                print(f"⚠️  '{requested_model}' no disponible para este proyecto/API key. "
                      f"Usando '{model}' en su lugar.")
            return model
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            errors.append(f"{model}: HTTP {e.code}: {body[:300]}")
            continue
    raise RuntimeError(
        "Ninguno de estos modelos respondió bien:\n  " + "\n  ".join(errors) +
        f"\nCorre 'curl https://generativelanguage.googleapis.com/v1beta/models -H \"x-goog-api-key: $GEMINI_API_KEY\"' "
        f"para ver qué modelos tiene disponibles tu API key y pasa uno con --model."
    )


def call_gemini(model: str, prompt: str, api_key: str, timeout: float, thinking_budget: int = 0):
    url = f"{API_BASE}/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "thinkingConfig": {"thinkingBudget": thinking_budget},
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_text(response_json: dict) -> str:
    candidates = response_json.get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    texts = []
    for p in parts:
        # Con thinkingBudget=0 no deberían venir parts "thought", pero por si
        # acaso se filtran explícitamente para no contaminar la predicción.
        if p.get("thought"):
            continue
        if "text" in p:
            texts.append(p["text"])
    return "\n".join(texts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--checkout", required=True)
    ap.add_argument("--logs-dir", default=None)
    ap.add_argument("--predictions-dir", required=True)
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--thinking-budget", type=int, default=0,
                     help="0 = thinking apagado (default, para comparar 'modelo pelado' vs Claude Code). "
                          "-1 = thinking dinámico (como usa Gemini CLI por defecto).")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Falta la variable de entorno GEMINI_API_KEY.")
        return

    os.makedirs(args.predictions_dir, exist_ok=True)
    with open(args.manifest, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if args.limit:
        rows = rows[: args.limit]

    try:
        resolved_model = resolve_model(args.model, api_key, args.timeout)
    except RuntimeError as e:
        print(f"❌ {e}")
        return
    args.model = resolved_model

    print(f"Modelo: {args.model} | thinking_budget: {args.thinking_budget} | programas: {len(rows)}")

    ok = 0
    for row in rows:
        program_key = row["program_key"]
        out_path = os.path.join(args.predictions_dir, f"{program_key}.md")
        if os.path.exists(out_path) and not args.force:
            print(f"skip {program_key} (ya tiene predicción)")
            ok += 1
            continue

        src_path = os.path.join(args.checkout, row["rel_path"], row["source_file"])
        if not os.path.exists(src_path):
            print(f"{program_key}: no existe {src_path}")
            continue
        with open(src_path, encoding="utf-8") as f:
            source_text = f.read()

        log_text = None
        if args.logs_dir:
            log_path = os.path.join(args.logs_dir, f"{program_key}.log")
            if os.path.exists(log_path):
                with open(log_path, encoding="utf-8") as lf:
                    log_text = lf.read()

        prompt = build_prompt(row["source_file"], source_text, log_text)

        last_err = None
        for attempt in range(args.retries):
            try:
                resp = call_gemini(args.model, prompt, api_key, args.timeout, args.thinking_budget)
                text = extract_text(resp)
                if not text.strip():
                    debug_path = os.path.join(args.predictions_dir, f"{program_key}.debug.txt")
                    with open(debug_path, "w", encoding="utf-8") as f:
                        json.dump(resp, f, ensure_ascii=False, indent=2)
                    print(f"{program_key}: respuesta vacía (ver {debug_path}), no se guarda")
                    break
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"{program_key}: guardado ({len(text)} chars)")
                ok += 1
                break
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                last_err = f"HTTP {e.code}: {body}"
                if e.code == 429 and attempt < args.retries - 1:
                    wait = 5 * (attempt + 1)
                    print(f"{program_key}: 429, reintentando en {wait}s...")
                    time.sleep(wait)
                    continue
                debug_path = os.path.join(args.predictions_dir, f"{program_key}.debug.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(last_err)
                print(f"{program_key}: error — detalle en {debug_path}")
                break
            except Exception as e:
                last_err = str(e)
                if attempt < args.retries - 1:
                    time.sleep(3)
                    continue
                debug_path = os.path.join(args.predictions_dir, f"{program_key}.debug.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(last_err)
                print(f"{program_key}: error — detalle en {debug_path}")

    print(f"\nTerminado. {ok}/{len(rows)} programas con predicción en {args.predictions_dir}")


if __name__ == "__main__":
    main()
