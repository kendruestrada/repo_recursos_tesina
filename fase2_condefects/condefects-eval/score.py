#!/usr/bin/env python3
"""
score.py — Calcula Top-N fault localization (Top-1/3/5) comparando las líneas
predichas por BugWizard (o cualquier sistema) contra la línea gold de ConDefects.

Entradas:
  - manifest.csv  (generado por build_manifest.py): program_key, gold_lines, ...
  - predictions/  : un archivo <program_key>.md por programa con la salida cruda
                    del sistema. Se parsea con adapter.extract_predicted_lines.

Métrica:
  - hit@N = 1 si alguna línea gold está entre las primeras N líneas predichas.
  - Se reporta accuracy Top-1/Top-3/Top-5 sobre el total de programas del
    manifiesto. Los programas sin archivo de predicción cuentan como fallo
    (0) por defecto — así el denominador es siempre el dataset completo
    (se puede cambiar con --skip-missing).

Salidas:
  - report.csv por programa (gold, predichas, hit@1/3/5, estado).
  - Resumen por consola (y por dificultad si el manifiesto trae 'task').

Uso:
  python3 score.py -m manifest.csv -p predictions/ -o report.csv \
        --checkout ../ConDefects/Code \
        [--system bugwizard] [--topn 1 3 5] [--skip-missing]

--checkout habilita el contrato nuevo (LINEAS_FALLA_TEXTO: se resuelve contra
el archivo fuente real, ver adapter.resolve_line_numbers). Si se omite, solo
se reconoce el contrato viejo (LINEAS_FALLA: [12, 5, 30]).
"""
from __future__ import annotations  # permite "tuple[...]" / "str | None" en Python < 3.10

import argparse
import csv
import os
from typing import List, Optional

from adapter import extract_predicted_lines, extract_predicted_line_texts, resolve_line_numbers


def parse_gold(gold_str: str) -> List[int]:
    return [int(x) for x in gold_str.split(";") if x.strip()]


def hit_at_n(pred: List[int], gold: List[int], n: int) -> bool:
    return any(g in pred[:n] for g in gold)


def load_prediction(
    pred_dir: str,
    program_key: str,
    source_path: Optional[str] = None,
) -> tuple[str, List[int]]:
    """Devuelve (estado, lineas). estado: 'ok' | 'missing' | 'empty'.

    Intenta primero el contrato nuevo (LINEAS_FALLA_TEXTO, resuelto contra
    source_path si se provee); si no hay bloque de texto o no se pudo resolver
    ninguna línea, cae al contrato viejo (LINEAS_FALLA con números) por
    compatibilidad con corridas previas o sistemas que lo ignoren.
    """
    path = os.path.join(pred_dir, f"{program_key}.md")
    if not os.path.exists(path):
        # también aceptamos .txt por comodidad
        alt = os.path.join(pred_dir, f"{program_key}.txt")
        if os.path.exists(alt):
            path = alt
        else:
            return "missing", []
    # En carpetas montadas en red (p. ej. la carpeta de trabajo sincronizada)
    # a veces os.path.exists() ve una entrada de directorio en caché mientras
    # open() todavía falla con ENOENT (stale handle). Reintenta un par de
    # veces antes de rendirse, para no tirar abajo TODO el scoring por un
    # archivo puntual con un hipo transitorio del filesystem.
    import time
    last_err = None
    for attempt in range(3):
        try:
            text = open(path, encoding="utf-8").read()
            break
        except OSError as e:
            last_err = e
            time.sleep(0.5 * (attempt + 1))
    else:
        print(f"⚠️  {program_key}: no se pudo leer {path} tras 3 intentos ({last_err}); se cuenta como 'missing'")
        return "missing", []

    if source_path and os.path.exists(source_path):
        texts = extract_predicted_line_texts(text)
        if texts:
            source_text = open(source_path, encoding="utf-8").read()
            lines = resolve_line_numbers(texts, source_text)
            if lines:
                return "ok", lines

    lines = extract_predicted_lines(text)
    return ("ok" if lines else "empty"), lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--manifest", required=True)
    ap.add_argument("-p", "--predictions", required=True, help="directorio con <program_key>.md")
    ap.add_argument("-o", "--output", required=True, help="report.csv de salida")
    ap.add_argument("--checkout", default=None,
                    help="dir del checkout de ConDefects (Code/), para resolver LINEAS_FALLA_TEXTO contra el archivo fuente real")
    ap.add_argument("--system", default="system", help="nombre del sistema evaluado (para el reporte)")
    ap.add_argument("--topn", type=int, nargs="+", default=[1, 3, 5])
    ap.add_argument("--skip-missing", action="store_true",
                    help="excluir del denominador los programas sin predicción")
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))

    topn = sorted(set(args.topn))
    report_rows = []
    totals = {n: 0 for n in topn}
    counted = 0
    n_missing = 0

    # acumuladores por dificultad (easy/middle/hard aprox. por si se quiere;
    # aquí agrupamos por 'task' para desglose opcional)
    by_task = {}

    for row in manifest:
        key = row["program_key"]
        gold = parse_gold(row["gold_lines"])
        source_path = None
        if args.checkout and row.get("rel_path") and row.get("source_file"):
            source_path = os.path.join(args.checkout, row["rel_path"], row["source_file"])
        status, pred = load_prediction(args.predictions, key, source_path)

        if status == "missing":
            n_missing += 1
            if args.skip_missing:
                report_rows.append({
                    "program_key": key, "task": row.get("task", ""),
                    "gold_lines": row["gold_lines"], "predicted": "", "status": "missing",
                    **{f"hit@{n}": "" for n in topn},
                })
                continue

        counted += 1
        hits = {n: hit_at_n(pred, gold, n) for n in topn}
        for n in topn:
            totals[n] += int(hits[n])

        task = row.get("task", "")
        d = by_task.setdefault(task, {"n": 0, **{n: 0 for n in topn}})
        d["n"] += 1
        for n in topn:
            d[n] += int(hits[n])

        report_rows.append({
            "program_key": key, "task": task,
            "gold_lines": row["gold_lines"],
            "predicted": ";".join(str(x) for x in pred),
            "status": status,
            **{f"hit@{n}": int(hits[n]) for n in topn},
        })

    # escribir report.csv
    fields = ["program_key", "task", "gold_lines", "predicted", "status"] + [f"hit@{n}" for n in topn]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(report_rows)

    # resumen
    print(f"\nSistema: {args.system}")
    print(f"Programas en manifiesto: {len(manifest)} | evaluados: {counted} | sin predicción: {n_missing}")
    if args.skip_missing:
        print("(modo --skip-missing: los faltantes NO cuentan en el denominador)")
    print("-" * 40)
    print(f"{'Métrica':<10}{'Aciertos':<12}{'Accuracy':<10}")
    print("-" * 40)
    for n in topn:
        acc = totals[n] / counted if counted else 0.0
        print(f"{'Top-'+str(n):<10}{totals[n]:<12}{acc:.2%}")
    print("-" * 40)
    print(f"Reporte por programa: {args.output}")


if __name__ == "__main__":
    main()
