#!/usr/bin/env python3
"""
run_cli_baseline.py — Corre Claude Code o Gemini CLI en modo headless (source-only)
sobre el mismo subconjunto de ConDefects usado para BugWizard, con el mismo
prompt y el mismo log "con síntoma" (generate_test_logs.py), para poder
comparar los tres sistemas con score.py en igualdad de condiciones.

Fairness / condiciones iguales para los 3 sistemas:
  - Se copia SOLO faultyVersion.{py,java} a un directorio temporal limpio y
    vacío — nunca correctVersion.* ni faultLocation.txt (igual que hace
    condefects-runner para BugWizard, ver su README).
  - El prompt es el mismo DEFAULT_PROMPT que usa condefects-runner/src/index.ts
    (pide el bloque "ARCHIVO: / LINEAS_FALLA: [...]"), más el contenido del
    MISMO log por-programa generado con generate_test_logs.py (logs/<program_key>.log).
    Así los tres sistemas reciben exactamente la misma información: código +
    síntoma (casos de test exitosos/fallidos), nada más.
  - Cada CLI corre restringido a herramientas de solo lectura (ver más abajo),
    para que sea una comparación de diagnóstico, no de "quién puede arreglar
    el archivo directamente".
  - La respuesta cruda se guarda como predictions_<carpeta>/<program_key>.md,
    con el mismo formato que usa BugWizard, para reusar adapter.py/score.py
    sin cambios.

Modelo (importante para comparar contra BugWizard sin darle ventaja a Claude
Code): BugWizard usa `anthropic.claude-sonnet-4-20250514-v1:0` vía AWS Bedrock
(ver condefects-runner/README.md). Ese snapshot está RETIRADO en la API directa
de Anthropic desde el 15/06/2026, pero Bedrock tiene su propio calendario de
retiro y BugWizard lo sigue usando ahí. Para igualar el modelo exactamente,
correr Claude Code también contra Bedrock, con el MISMO inference profile:

    export CLAUDE_CODE_USE_BEDROCK=1
    export AWS_PROFILE=DevRole-123456789012   # o el perfil con acceso al mismo Bedrock
    export AWS_REGION=us-east-1
    python3 run_cli_baseline.py --agent claude \
        --model 'arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0' \
        --manifest manifest_subset.csv --checkout ../ConDefects/Code \
        --logs-dir logs --predictions-dir predictions_claude_code

Si no tienes ese acceso AWS, usa el modelo activo más cercano en la API directa
(--model claude-sonnet-4-5-20250929) y documenta la diferencia como limitación.

Para Gemini CLI (sin restricción de modelo pedida por el usuario, pero verifica
antes que el comando `gemini` en tu máquina siga siendo el clásico Gemini CLI y
no haya sido migrado a Antigravity CLI — Google anunció ese reemplazo para
cuentas gratuitas/Google One a mediados de 2026):

    python3 run_cli_baseline.py --agent gemini --model gemini-2.5-pro \
        --manifest manifest_subset.csv --checkout ../ConDefects/Code \
        --logs-dir logs --predictions-dir predictions_gemini_cli

Luego puntuar cada sistema por separado:
    python3 score.py -m manifest_subset.csv -p predictions_claude_code -o report_claude_code.csv --system claude-code
    python3 score.py -m manifest_subset.csv -p predictions_gemini_cli  -o report_gemini_cli.csv  --system gemini-cli
"""
from __future__ import annotations  # permite "str | None" en type hints con Python < 3.10

import argparse
import csv
import os
import shutil
import subprocess
import tempfile

# NOTA: se pide el TEXTO de la línea, no el número (mismo motivo y mismo
# prompt que condefects-runner/src/index.ts — ver el comentario ahí). Debe
# ser IDÉNTICO al de BugWizard para que la comparación sea justa.
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


def build_prompt(source_filename: str, log_text: str | None) -> str:
    # Se referencia el archivo con "@nombre" (sintaxis de mención de archivo
    # soportada tanto por Claude Code como por Gemini CLI) para que el
    # contenido se inyecte directamente en el mensaje, SIN que el modelo
    # tenga que invocar una herramienta de lectura. Esto evita depender de
    # una vuelta de tool-use en modo headless (que fue justamente la causa
    # del error de "thinking block" con Claude Code al combinarse con
    # --max-turns) y evita la incertidumbre de si --approval-mode plan de
    # Gemini CLI llegaría a ejecutar una herramienta de lectura o no.
    parts = [
        DEFAULT_PROMPT,
        "",
        f"El archivo de código a analizar es @{source_filename} "
        f"(adjunto arriba/abajo con su contenido completo).",
        "",
        "Log de ejecución disponible (casos de prueba exitosos y fallidos reales):",
        "---",
        (log_text.strip() if log_text else "sin logs"),
        "---",
    ]
    return "\n".join(parts)


def run_claude(prompt: str, workdir: str, model: str | None, max_turns: int, timeout: float):
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "text",
        "--tools", "Read",
        "--permission-mode", "bypassPermissions",  # seguro: --tools ya limita a solo-lectura
        "--max-turns", str(max_turns),
    ]
    if model:
        cmd += ["--model", model]
    env = os.environ.copy()
    # Extended thinking + tool use + --max-turns puede cortar la conversación
    # justo cuando el mensaje final del asistente debería empezar con un
    # bloque "thinking" (requisito de la API cuando thinking está activo),
    # produciendo: "API Error: 400 ... Expected `thinking` or
    # `redacted_thinking`, but found `text`". La recomendación oficial de
    # Anthropic es desactivar thinking; MAX_THINKING_TOKENS=0 lo hace también
    # en Bedrock. La tarea es simple (leer un archivo corto y diagnosticar),
    # no necesita extended thinking.
    env["MAX_THINKING_TOKENS"] = "0"
    return subprocess.run(
        cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout,
        stdin=subprocess.DEVNULL,  # evita el warning/espera de "no stdin data" en modo headless
        env=env,
    )


def run_gemini(prompt: str, workdir: str, model: str | None, timeout: float):
    cmd = [
        "gemini", "-p", prompt,
        "--output-format", "text",
        "--approval-mode", "plan",  # evita que ejecute ediciones; solo diagnostica
        # cada corrida usa un directorio temporal nuevo -> Gemini CLI lo trata
        # como "no confiable" y baja el approval-mode a "default", lo que
        # cuelga/falla en modo headless (no hay TTY para aprobar). --skip-trust
        # evita ese chequeo para automatización.
        "--skip-trust",
    ]
    if model:
        cmd += ["--model", model]
    return subprocess.run(
        cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout,
        stdin=subprocess.DEVNULL,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True, choices=["claude", "gemini"])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--checkout", required=True)
    ap.add_argument("--logs-dir", default=None, help="carpeta con <program_key>.log (de generate_test_logs.py)")
    ap.add_argument("--predictions-dir", required=True)
    ap.add_argument("--model", default=None, help="ID/alias/ARN de modelo; si se omite, usa el default del CLI")
    ap.add_argument("--max-turns", type=int, default=6, help="solo aplica a --agent claude")
    ap.add_argument("--timeout", type=float, default=180.0, help="segundos por programa")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true",
                     help="regenerar (sobrescribir) predicciones que ya existen, en vez de saltarlas. "
                          "Util para invalidar corridas previas (p. ej. hechas antes de bloquear WebSearch) "
                          "sin tener que borrar archivos a mano.")
    args = ap.parse_args()

    os.makedirs(args.predictions_dir, exist_ok=True)
    with open(args.manifest, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if args.limit:
        rows = rows[: args.limit]

    print(f"Agente: {args.agent} | modelo: {args.model or '(default del CLI)'} | programas: {len(rows)}")

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

        log_text = None
        if args.logs_dir:
            log_path = os.path.join(args.logs_dir, f"{program_key}.log")
            if os.path.exists(log_path):
                with open(log_path, encoding="utf-8") as lf:
                    log_text = lf.read()

        with tempfile.TemporaryDirectory(prefix=f"condefects-{program_key}-") as tmp:
            dest = os.path.join(tmp, row["source_file"])
            shutil.copy(src_path, dest)  # SOLO el archivo fallado, nada más en el directorio

            prompt = build_prompt(row["source_file"], log_text)

            try:
                if args.agent == "claude":
                    proc = run_claude(prompt, tmp, args.model, args.max_turns, args.timeout)
                else:
                    proc = run_gemini(prompt, tmp, args.model, args.timeout)
            except FileNotFoundError:
                print(f"❌ No se encontró el comando '{args.agent}' en el PATH. ¿Está instalado?")
                return
            except subprocess.TimeoutExpired as te:
                # Guardar lo que se haya alcanzado a capturar (stdout/stderr
                # parciales) para poder diagnosticar SI el proceso estaba
                # realmente "pensando" (poca/ninguna salida) o atascado en un
                # loop de reintentos/errores (stderr con mensajes repetidos).
                debug_path = os.path.join(args.predictions_dir, f"{program_key}.timeout.txt")
                partial_out = (te.stdout or b"")
                partial_err = (te.stderr or b"")
                if isinstance(partial_out, bytes):
                    partial_out = partial_out.decode("utf-8", errors="ignore")
                if isinstance(partial_err, bytes):
                    partial_err = partial_err.decode("utf-8", errors="ignore")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(f"TIMEOUT (agente={args.agent}, > {args.timeout}s)\n\n")
                    f.write("=== STDOUT parcial ===\n")
                    f.write(partial_out or "(vacio)")
                    f.write("\n=== STDERR parcial ===\n")
                    f.write(partial_err or "(vacio)")
                print(f"{program_key}: TIMEOUT (> {args.timeout}s) — parcial en {debug_path}")
                continue

            if proc.returncode != 0:
                # No guardar el error como si fuera una predicción válida.
                # Se guarda stdout+stderr COMPLETOS a un .debug.txt para poder
                # diagnosticar sin tener que reproducir el fallo a mano — un
                # mensaje truncado a 300 chars puede esconder el error real
                # (p. ej. si primero sale un warning benigno de deprecación de
                # modelo y el error real viene después).
                debug_path = os.path.join(args.predictions_dir, f"{program_key}.debug.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(f"CMD (agente={args.agent}, rc={proc.returncode})\n\n")
                    f.write("=== STDOUT ===\n")
                    f.write(proc.stdout)
                    f.write("\n=== STDERR ===\n")
                    f.write(proc.stderr)
                print(f"{program_key}: error (rc={proc.returncode}) — detalle completo en {debug_path}")
                continue

            if not proc.stdout.strip():
                print(f"{program_key}: respuesta vacía, no se guarda")
                continue

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(proc.stdout)
            print(f"{program_key}: guardado ({len(proc.stdout)} chars)")
            ok += 1

    print(f"\nTerminado. {ok}/{len(rows)} programas con predicción en {args.predictions_dir}")


if __name__ == "__main__":
    main()
