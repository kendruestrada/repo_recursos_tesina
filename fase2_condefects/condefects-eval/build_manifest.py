#!/usr/bin/env python3
"""
build_manifest.py — Construye el manifiesto de ground truth a partir de un
checkout de ConDefects.

Layout esperado (tras `python3 ConDefects.py checkout -w <dest> -l python`):

    <dest>/<task>/<language>/<programID>/
        faultyVersion.py      (o .java)
        correctVersion.py     (o .java)
        faultLocation.txt     (entero, línea 1-based de la falla)

Salida: un CSV con una fila por programa:
    program_key,task,language,program_id,source_file,gold_lines,rel_path

- program_key: identificador estable  = <task>__<language>__<programID>.
  Se usa también para nombrar el archivo de predicción de BugWizard
  (<program_key>.md) que consumirá score.py.
- gold_lines: línea(s) de falla 1-based, separadas por ';' (normalmente una).

Uso:
    python3 build_manifest.py -w <checkout_dir> -o manifest.csv [-l python]
"""
import argparse
import csv
import os
import re


def read_gold_lines(fault_location_path: str):
    """Lee faultLocation.txt y devuelve la lista de líneas gold (1-based).

    Info.py del toolkit lee una sola línea, pero por robustez tomamos todos
    los enteros presentes en el archivo (por si hubiera múltiples fallas).
    """
    with open(fault_location_path, "r", encoding="utf-8") as f:
        content = f.read()
    nums = [int(n) for n in re.findall(r"-?\d+", content)]
    return nums


def find_source_file(program_dir: str):
    for name in ("faultyVersion.py", "faultyVersion.java"):
        p = os.path.join(program_dir, name)
        if os.path.exists(p):
            lang = "python" if name.endswith(".py") else "java"
            return name, lang
    return None, None


def build(checkout_dir: str, language_filter: str | None):
    rows = []
    for root, _dirs, files in os.walk(checkout_dir):
        if "faultLocation.txt" not in files:
            continue
        source_file, lang = find_source_file(root)
        if source_file is None:
            # carpeta sin código reconocible: se ignora
            continue
        if language_filter and lang != language_filter:
            continue

        rel = os.path.relpath(root, checkout_dir)
        parts = rel.split(os.sep)
        # rel esperado: <task>/<language>/<programID>
        if len(parts) >= 3:
            task, lang_dir, program_id = parts[0], parts[1], parts[-1]
        else:
            task, lang_dir, program_id = parts[0], lang, parts[-1]

        gold = read_gold_lines(os.path.join(root, "faultLocation.txt"))
        if not gold:
            continue

        program_key = f"{task}__{lang}__{program_id}"
        rows.append({
            "program_key": program_key,
            "task": task,
            "language": lang,
            "program_id": program_id,
            "source_file": source_file,
            "gold_lines": ";".join(str(n) for n in gold),
            "rel_path": rel,
        })
    rows.sort(key=lambda r: r["program_key"])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-w", "--checkout-dir", required=True, help="directorio del checkout de ConDefects")
    ap.add_argument("-o", "--output", required=True, help="ruta del manifest.csv de salida")
    ap.add_argument("-l", "--language", choices=["python", "java"], default=None,
                    help="filtrar por lenguaje (opcional)")
    args = ap.parse_args()

    rows = build(args.checkout_dir, args.language)
    fields = ["program_key", "task", "language", "program_id", "source_file", "gold_lines", "rel_path"]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Manifiesto escrito: {args.output}  ({len(rows)} programas)")


if __name__ == "__main__":
    main()
