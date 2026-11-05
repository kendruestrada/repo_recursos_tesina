#!/usr/bin/env python3
"""
generate_test_logs.py — Genera logs de prueba (casos exitosos y fallidos) para
alimentar a BugWizard, usando datos reales de ConDefects.

Toma un manifiesto (formato de build_manifest.py: program_key, task, language,
program_id, source_file, gold_lines, rel_path), ejecuta faultyVersion.py de
cada programa contra los test cases reales (extraídos de Test.zip) y arma un
log de texto compacto por programa:

  - Resumen de TODOS los test cases (OK/FAIL) -> le da a BugWizard una idea
    completa del comportamiento sin gastar tokens en el detalle de cada uno.
  - Detalle completo (entrada / esperado / obtenido) SOLO de hasta 3 casos
    fallidos y 1 caso exitoso de referencia -> lo mínimo necesario para que
    el modelo entienda el problema real.

Uso:
    python3 generate_test_logs.py \
        --manifest manifest_subset.csv \
        --checkout ../ConDefects/Code \
        --test-root ../testcondefects/Test \
        --out-dir logs \
        --timeout 5
"""
import argparse
import csv
import os
import subprocess


def read_lines(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().splitlines()


def truncate(text, limit=400):
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... (truncado, {len(text)} chars totales)"


def find_test_dir(test_root, task):
    parts = task.split("_")
    contest, letter = parts[0], parts[1].upper()
    d = os.path.join(test_root, contest, letter)
    if not os.path.isdir(d):
        d = os.path.join(test_root, contest, "Ex")
    return d


def run_case(src_path, input_path, timeout):
    try:
        with open(input_path, "rb") as f:
            data = f.read()
        p = subprocess.run(
            ["python3", src_path],
            input=data,
            capture_output=True,
            timeout=timeout,
        )
        stdout = p.stdout.decode("utf-8", errors="ignore")
        stderr = p.stderr.decode("utf-8", errors="ignore")
        return stdout, stderr, p.returncode, False
    except subprocess.TimeoutExpired:
        return "", f"(timeout > {timeout}s, posible loop infinito)", None, True


def build_results(src_path, test_dir, timeout, max_cases=None):
    in_dir = os.path.join(test_dir, "in")
    out_dir = os.path.join(test_dir, "out")
    tests = sorted(os.listdir(in_dir))
    if max_cases:
        # muestreo espaciado (no solo los primeros) para no sesgar hacia
        # los casos "sample" iniciales, que suelen ser los mas chicos/faciles
        if len(tests) > max_cases:
            step = len(tests) / max_cases
            tests = [tests[int(i * step)] for i in range(max_cases)]
    results = []
    for t in tests:
        in_path = os.path.join(in_dir, t)
        out_path = os.path.join(out_dir, t)
        if not os.path.exists(out_path):
            continue
        stdout, stderr, rc, timed_out = run_case(src_path, in_path, timeout)
        expected = read_lines(out_path)
        actual = stdout.splitlines()
        ok = (not timed_out) and (rc == 0) and (expected == actual)
        results.append(
            {
                "name": t,
                "ok": ok,
                "stdout": stdout,
                "stderr": stderr,
                "rc": rc,
                "timed_out": timed_out,
                "in": read_lines(in_path),
                "expected": expected,
            }
        )
    return results


def format_log(program_key, task, results):
    lines = []
    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    lines.append(f"=== Log de ejecucion: {program_key} (tarea {task}) ===")
    lines.append(
        f"Casos ejecutados: {total} | Exitosos: {passed} | Fallidos: {total - passed}"
    )
    lines.append("")
    lines.append("Resumen por caso:")
    for r in results:
        status = "OK" if r["ok"] else "FAIL"
        lines.append(f"  [{status}] {r['name']}")

    fails = [r for r in results if not r["ok"]]
    oks = [r for r in results if r["ok"]]

    if fails:
        lines.append("")
        lines.append("--- Detalle de casos FALLIDOS ---")
        for r in fails[:3]:
            lines.append(f"\n[FALLIDO] {r['name']}")
            lines.append("entrada:")
            lines.append(truncate("\n".join(r["in"])))
            lines.append("esperado:")
            lines.append(truncate("\n".join(r["expected"])))
            if r["timed_out"]:
                lines.append("obtenido: (timeout, posible loop infinito)")
            elif r["stderr"].strip():
                lines.append("obtenido: (excepcion / stderr)")
                lines.append(truncate(r["stderr"]))
            else:
                lines.append("obtenido:")
                lines.append(truncate("\n".join(r["stdout"].splitlines())))

    if oks:
        r = oks[0]
        lines.append("")
        lines.append(f"[EXITOSO] {r['name']} (caso de referencia)")
        lines.append("entrada:")
        lines.append(truncate("\n".join(r["in"]), 150))
        lines.append("salida:")
        lines.append(truncate("\n".join(r["stdout"].splitlines()), 150))

    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--checkout", required=True)
    ap.add_argument("--test-root", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("--skip-existing", action="store_true",
                     help="no regenerar <program_key>.log si ya existe (permite reanudar corridas largas en varias invocaciones)")
    ap.add_argument("--max-cases", type=int, default=None,
                     help="limitar a N test cases por programa (muestreo espaciado), para acotar el tiempo en problemas con muchos/pesados casos")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))

    for row in rows:
        program_key = row["program_key"]
        if row["language"] != "python":
            print(f"skip {program_key} (solo se soporta python por ahora)")
            continue
        out_path_check = os.path.join(args.out_dir, f"{program_key}.log")
        if args.skip_existing and os.path.exists(out_path_check):
            print(f"skip {program_key} (log ya existe)")
            continue
        task = row["task"]
        src_path = os.path.join(args.checkout, row["rel_path"], row["source_file"])
        if not os.path.exists(src_path):
            print(f"no existe {src_path}")
            continue
        test_dir = find_test_dir(args.test_root, task)
        in_dir = os.path.join(test_dir, "in")
        if not os.path.isdir(in_dir):
            print(f"{program_key}: no hay test dir en {test_dir}")
            continue
        results = build_results(src_path, test_dir, args.timeout, args.max_cases)
        if not results:
            print(f"{program_key}: sin resultados")
            continue
        text = format_log(program_key, task, results)
        out_path = os.path.join(args.out_dir, f"{program_key}.log")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        passed = sum(1 for r in results if r["ok"])
        print(f"{program_key}: {passed}/{len(results)} OK -> {out_path}")


if __name__ == "__main__":
    main()
