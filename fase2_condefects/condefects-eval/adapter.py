#!/usr/bin/env python3
"""
adapter.py — Extrae las líneas de falla predichas desde la salida (markdown)
de un sistema (BugWizard, Claude Code, Gemini CLI, etc.), en orden de
confianza (la primera = más probable).

Por qué texto y no número de línea
-----------------------------------
El contrato original le pedía al sistema el NÚMERO de línea directamente
(`LINEAS_FALLA: [12, 5, 30]`). Eso es injusto para sistemas que arman el
contexto vía RAG/chunking (como BugWizard): perdimos numeración verbatim al
indexar+recuperar el código, así que el modelo tiene que CONTAR líneas sobre
un texto que puede no conservar el mapeo 1:1 al archivo original — y en la
práctica eso produce errores sistemáticos de conteo (off-by-one, atribuir el
bug a la línea de control `if`/`else` de al lado) aunque el diagnóstico
semántico sea correcto. Confirmado revisando las transcripciones reales de
BugWizard en este dataset.

Para que la comparación mida "¿encontró el bug?" y no "¿supo contar líneas?",
el contrato ahora le pide al sistema el TEXTO EXACTO de la línea (no el
número), y este módulo resuelve ese texto a un número de línea buscándolo
directamente en el archivo fuente real. Contrato recomendado:

    ARCHIVO: faultyVersion.py
    LINEAS_FALLA_TEXTO:
    1. "print('NO')"
    2. "if d['R'] > d['M']:"
    3. "n += 1"

El parser es robusto: si no encuentra el bloque de texto, cae al contrato
viejo (`LINEAS_FALLA: [12, 5, 30]`, por si un sistema lo ignora y responde con
números de todas formas), y si tampoco hay eso, a heurísticas de texto libre
("línea 12", "line 12", "L12"). Devuelve listas deduplicadas preservando
orden.
"""
from __future__ import annotations  # permite "str | None" en type hints con Python < 3.10

import difflib
import re
from typing import List, Optional

# Bloque estructurado nuevo (texto exacto de la línea, no el número).
# El (?!_TEXTO) evita que el regex del contrato viejo (_LINEAS_FALLA_RE) haga
# match parcial sobre el encabezado "LINEAS_FALLA_TEXTO:".
_LINEAS_FALLA_TEXTO_RE = re.compile(r"LINEAS?_FALLA_TEXTO\s*:?\s*\n?(.*?)(?:\n\s*\n|\Z)", re.IGNORECASE | re.DOTALL)
_LIST_ITEM_RE = re.compile(r"""^\s*(?:\d+[.)]|[-*])?\s*["'`]?(.*?)["'`]?\s*$""")

# Bloque estructurado viejo (número de línea directo). Se mantiene como
# respaldo por si un sistema ignora el contrato nuevo y responde con números
# igual. El "(?!_TEXTO)" evita hacer match parcial sobre "LINEAS_FALLA_TEXTO:".
_LINEAS_FALLA_RE = re.compile(r"LINEAS?_FALLA(?!_TEXTO)\s*:?\s*(.+)", re.IGNORECASE)
_ARCHIVO_RE = re.compile(r"ARCHIVO\s*:?\s*(.+)", re.IGNORECASE)

# Heurísticas de respaldo sobre texto libre.
_FALLBACK_PATTERNS = [
    re.compile(r"l[íi]nea?s?\s*#?\s*(\d+)", re.IGNORECASE),   # "línea 12", "lineas 12"
    re.compile(r"\bline\s*#?\s*(\d+)", re.IGNORECASE),        # "line 12"
    re.compile(r"\bL\s*(\d+)\b"),                              # "L12"
]


def _dedup_keep_order(nums: List[int]) -> List[int]:
    seen = set()
    out = []
    for n in nums:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def extract_predicted_lines(text: str) -> List[int]:
    """Devuelve la lista ordenada de líneas predichas (1-based)."""
    if not text:
        return []

    # 1) Bloque estructurado LINEAS_FALLA (tomamos la última ocurrencia,
    #    que suele ser la conclusión final del agente).
    matches = _LINEAS_FALLA_RE.findall(text)
    if matches:
        payload = matches[-1]
        nums = [int(n) for n in re.findall(r"\d+", payload)]
        if nums:
            return _dedup_keep_order(nums)

    # 2) Respaldo: recorrer el texto y recolectar líneas mencionadas en orden.
    hits = []  # (posición, número)
    for pat in _FALLBACK_PATTERNS:
        for m in pat.finditer(text):
            hits.append((m.start(), int(m.group(1))))
    hits.sort(key=lambda h: h[0])
    return _dedup_keep_order([n for _pos, n in hits])


def extract_predicted_file(text: str) -> str | None:
    if not text:
        return None
    m = _ARCHIVO_RE.search(text)
    if m:
        return m.group(1).strip().strip("`").strip()
    return None


def _dedup_keep_order_str(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for it in items:
        key = it.strip()
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def extract_predicted_line_texts(text: str) -> List[str]:
    """Extrae el TEXTO exacto de línea predicho por el bloque
    LINEAS_FALLA_TEXTO (contrato nuevo), en orden de confianza. Cada ítem
    puede venir como lista numerada ("1. ...", "1) ..."), con viñeta ("- ...")
    o solo el texto entre comillas por línea. Se preserva el orden de
    aparición y se deduplica.
    """
    if not text:
        return []

    m = _LINEAS_FALLA_TEXTO_RE.search(text)
    if not m:
        return []

    block = m.group(1)
    items: List[str] = []
    for raw_line in block.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        m2 = _LIST_ITEM_RE.match(raw_line)
        candidate = m2.group(1).strip() if m2 else raw_line
        if candidate:
            items.append(candidate)
    return _dedup_keep_order_str(items)


def resolve_line_numbers(
    predicted_texts: List[str],
    source_text: str,
    fuzzy_threshold: float = 0.72,
) -> List[int]:
    """Resuelve una lista de textos de línea predichos a números de línea
    (1-based) BUSCÁNDOLOS en el archivo fuente real — así el sistema evaluado
    nunca tiene que contar líneas, solo identificar cuál es la línea con el
    bug (que es lo que realmente queremos medir).

    Estrategia por cada texto predicho:
      1. Match exacto contra alguna línea del archivo (ambos strip()eados).
         Si hay varias líneas idénticas (código repetitivo), se toma la
         primera ocurrencia — limitación conocida, documentada en el reporte.
      2. Si no hay match exacto, similaridad difflib contra todas las líneas;
         se toma la de mayor score si supera `fuzzy_threshold`.
      3. Si no se puede resolver, se descarta ese texto (no cuenta como
         predicción — es preferible a adivinar).

    Devuelve la lista de números de línea resueltos, deduplicada y en el
    mismo orden de confianza que `predicted_texts`.
    """
    source_lines = source_text.splitlines()
    stripped_source = [ln.strip() for ln in source_lines]

    resolved: List[int] = []
    for predicted in predicted_texts:
        target = predicted.strip()
        if not target:
            continue

        line_no: Optional[int] = None

        # 1) match exacto (primera ocurrencia)
        for i, s in enumerate(stripped_source):
            if s and s == target:
                line_no = i + 1
                break

        # 2) fallback difuso
        if line_no is None:
            best_ratio = 0.0
            best_idx = None
            for i, s in enumerate(stripped_source):
                if not s:
                    continue
                ratio = difflib.SequenceMatcher(None, s, target).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_idx = i
            if best_idx is not None and best_ratio >= fuzzy_threshold:
                line_no = best_idx + 1

        if line_no is not None:
            resolved.append(line_no)

    return _dedup_keep_order(resolved)


if __name__ == "__main__":
    import sys
    data = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
    print("archivo:", extract_predicted_file(data))
    print("lineas (numero, contrato viejo):", extract_predicted_lines(data))
    print("lineas (texto, contrato nuevo):", extract_predicted_line_texts(data))
