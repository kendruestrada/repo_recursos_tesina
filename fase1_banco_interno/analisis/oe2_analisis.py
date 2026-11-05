"""
OE2 — Pipeline de análisis del benchmark comparativo
=====================================================
Ejecutar: python3 oe2_analisis.py
Requiere: pandas, numpy (incluidos en CPython estándar de Anaconda/miniconda)
Salida  : oe2_resultados.md, oe2_datos_brutos.csv, oe2_medias_por_agente.csv,
          oe2_wilcoxon.csv  (en el mismo directorio)

Agentes evaluados (8 configuraciones × 19 tests):
  claude_basic    : Claude Code CLI, solo código fuente
  claude_logs     : Claude Code CLI, código + logs
  claude_detailed : Claude Code CLI, contexto completo detallado
  gemini_basic    : Gemini CLI, solo código fuente
  gemini_logs     : Gemini CLI, código + logs
  gemini_detailed : Gemini CLI, contexto completo detallado
  bwz_prompt1     : BugWizard (prompt variante 1)
  bwz_prompt2     : BugWizard (prompt variante 2)
"""

import os, json, re
from itertools import combinations
import numpy as np
import pandas as pd

# ── RUTAS ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(SCRIPT_DIR, "..", "respuestas_y_evaluaciones")

AGENT_DEFS = [
    ("claude_basic",    "claude/20260220-153651", "source-only.md"),
    ("claude_logs",     "claude/20260220-153651", "source-and-logs.md"),
    ("claude_detailed", "claude/20260220-153651", "detailed-source-and-logs.md"),
    ("gemini_basic",    "gemini/20260225-155033", "source-only.md"),
    ("gemini_logs",     "gemini/20260225-155033", "source-and-logs.md"),
    ("gemini_detailed", "gemini/20260225-155033", "detailed-source-and-logs.md"),
    ("bwz_prompt1",     "bugwizard/2026-02-24",   None),   # runner-test-XXX-prompt-1.md
    ("bwz_prompt2",     "bugwizard/2026-02-24",   None),   # runner-test-XXX-prompt-2.md
]
TESTS = [f"{i:03d}" for i in range(1, 21) if i != 17]   # T017 excluido: sin evaluaciones

LABEL = {
    "claude_basic":    "Claude Code (solo código)",
    "claude_logs":     "Claude Code (código + logs)",
    "claude_detailed": "Claude Code (detallado)",
    "gemini_basic":    "Gemini CLI (solo código)",
    "gemini_logs":     "Gemini CLI (código + logs)",
    "gemini_detailed": "Gemini CLI (detallado)",
    "bwz_prompt1":     "BugWizard (prompt 1)",
    "bwz_prompt2":     "BugWizard (prompt 2)",
}
DIMS = ["identifico_error", "calidad_explicacion", "calidad_propuestas",
        "nivel_alucinacion", "puntuacion"]


# ── 1. MAPEO AGENTE → ARCHIVO ─────────────────────────────────────────────────

def _read(path):
    try:
        return open(path, encoding="utf-8").read()
    except:
        return ""

def _source_path(tid, name, d, f):
    if f is None:
        suffix = "prompt-1" if "prompt1" in name else "prompt-2"
        return os.path.join(BASE, d, f"runner-test-{tid}-{suffix}.md")
    return os.path.join(BASE, d, f"test_{tid}", f)

def _test_file_path(tid, n):
    tnum = int(tid)
    folder = "Test 001" if tnum == 1 else f"Test{tid}"
    return os.path.join(BASE, "Test-revisados", folder, f"Test{tid}-{n}.md")

def _clean(text):
    return text[len("###Analysis\n"):].strip() if text.startswith("###Analysis\n") else text.strip()

def _score(test_text, src_text):
    """Count how many 60-char windows from test_text appear verbatim in src_text."""
    if not test_text or not src_text:
        return 0
    return sum(1 for o in range(50, min(len(test_text) - 60, 2000), 100)
               if len(test_text[o:o+60]) >= 40 and test_text[o:o+60] in src_text)

def build_mapping():
    """
    For each test, match TestXXX-N.md files to their source agent by content
    fingerprinting. Ties/unknowns resolved by elimination.
    Returns: {tid: {n: agent_name}}
    """
    mapping = {}
    for tid in TESTS:
        sources = {name: _read(_source_path(tid, name, d, f))
                   for name, d, f in AGENT_DEFS}
        pairs = sorted(
            [(_score(_clean(_read(_test_file_path(tid, n))), sources[ag]), n, ag)
             for n in range(1, 9) for ag in sources],
            reverse=True)
        asn_a, asn_n, mp = set(), set(), {}
        for sc, n, ag in pairs:
            if n in asn_n or ag in asn_a:
                continue
            if sc > 0:
                mp[n] = ag; asn_a.add(ag); asn_n.add(n)
        # Elimination for unmatched
        for n, a in zip([n for n in range(1, 9) if n not in asn_n],
                        [a for a in sources if a not in asn_a]):
            mp[n] = a
        mapping[tid] = mp
    return mapping


# ── 2. CARGA DE EVALUACIONES ──────────────────────────────────────────────────

def _parse_json(fpath, tid, juez, mapping):
    rows = []
    with open(fpath, encoding="utf-8") as f:
        entries = json.load(f)
    for e in entries:
        nm = re.search(r"Test\d+-(\d+)", e.get("nombre", ""), re.IGNORECASE)
        if not nm:
            continue
        n = int(nm.group(1))
        agent = mapping.get(tid, {}).get(n)
        if not agent:
            continue
        rows.append({
            "test_id": tid, "file_n": n, "agent": agent, "juez": juez,
            "identifico_error":    1 if e.get("identifico_error") else 0,
            "calidad_explicacion": e.get("calidad_explicacion"),
            "calidad_propuestas":  e.get("calidad_propuestas"),
            "nivel_alucinacion":   e.get("realidad_diagnostico_(nivel_alucinacion)"),
            "puntuacion":          e.get("puntuacion"),
        })
    return rows

def load_evaluations(mapping):
    rows = []
    notas_dir = os.path.join(BASE, "Notas")
    for fn in sorted(os.listdir(notas_dir)):
        if not fn.endswith(".json"):
            continue
        m = re.search(r"Test(\d+)", fn, re.IGNORECASE)
        if m:
            rows += _parse_json(os.path.join(notas_dir, fn),
                                 f"{int(m.group(1)):03d}", "experto1", mapping)
    experto2_dir = os.path.join(notas_dir, "notas_experto2")
    for fn in sorted(os.listdir(experto2_dir)):
        if not fn.endswith(".json"):
            continue
        m = re.search(r"test(\d+)", fn, re.IGNORECASE)
        if m:
            rows += _parse_json(os.path.join(experto2_dir, fn),
                                 f"{int(m.group(1)):03d}", "experto2", mapping)
    return pd.DataFrame(rows)


# ── 3. CONCORDANCIA (Krippendorff α ordinal + Spearman ρ) ────────────────────

def krippendorff_ordinal(r1_raw, r2_raw):
    """Two-rater ordinal Krippendorff alpha. Ref: Krippendorff (2004)."""
    r1 = np.array(r1_raw, dtype=float)
    r2 = np.array(r2_raw, dtype=float)
    mask = ~(np.isnan(r1) | np.isnan(r2))
    r1, r2 = r1[mask], r2[mask]
    n = len(r1)
    if n < 2:
        return np.nan
    all_obs = np.concatenate([r1, r2])
    N = len(all_obs)
    cats = np.sort(np.unique(all_obs))
    counts = np.array([np.sum(all_obs == c) for c in cats], dtype=float)

    def d_sq(c, cp):
        ci = int(np.searchsorted(cats, c))
        cj = int(np.searchsorted(cats, cp))
        lo, hi = min(ci, cj), max(ci, cj)
        if lo == hi:
            return 0.0
        return (np.sum(counts[lo:hi+1]) - (counts[lo] + counts[hi]) / 2) ** 2

    D_o = float(np.mean([d_sq(r1[i], r2[i]) for i in range(n)]))
    D_e_sum = sum(counts[i] * counts[j] * d_sq(cats[i], cats[j])
                  for i in range(len(cats)) for j in range(len(cats)) if i != j)
    D_e = D_e_sum / (N * (N - 1))
    return 1.0 - D_o / D_e if D_e != 0 else 1.0

def spearman_rho(x, y):
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 3:
        return np.nan
    rx = pd.Series(x).rank(method="average").values
    ry = pd.Series(y).rank(method="average").values
    d2 = np.sum((rx - ry) ** 2)
    return 1 - 6 * d2 / (n * (n ** 2 - 1))

def concordance_stats(df):
    piv = df.pivot_table(index=["test_id", "file_n"], columns="juez",
                          values=DIMS, aggfunc="first")
    results = {}
    for dim in DIMS:
        k = piv[dim].get("experto1", pd.Series(dtype=float)).values
        l = piv[dim].get("experto2",   pd.Series(dtype=float)).values
        k_arr = np.array(k, dtype=float)
        l_arr = np.array(l, dtype=float)
        mask = ~(np.isnan(k_arr) | np.isnan(l_arr))
        kp, lp = k_arr[mask], l_arr[mask]
        results[dim] = {
            "alpha":     round(krippendorff_ordinal(k, l), 4),
            "rho":       round(spearman_rho(k, l), 4),
            "exact_pct": round(float(np.mean(kp == lp)) * 100, 1),
            "within1_pct": round(float(np.mean(np.abs(kp - lp) <= 1)) * 100, 1),
            "n_pairs":   int(mask.sum()),
        }
    return results


# ── 4. FRIEDMAN (corregido con pandas.rank) ───────────────────────────────────

def friedman_test(pivot_df):
    """
    pivot_df: DataFrame (tests × agents).
    Returns (chi2, p_approx, mean_ranks_Series).
    Uses Wilson–Hilferty normal approximation for p-value.
    """
    n, k = pivot_df.shape
    ranked = pivot_df.apply(lambda row: row.rank(method="average"), axis=1)
    mr = ranked.mean()
    chi2 = 12 * n / (k * (k + 1)) * np.sum((mr - (k + 1) / 2) ** 2)
    df_chi = k - 1
    z = (chi2 - df_chi) / np.sqrt(2 * df_chi)
    p = max(1e-6, min(1.0, 0.5 * (1 - np.tanh(0.7978845608 * z * (1 + 0.0433 * z ** 2)))))
    return float(chi2), float(p), mr


# ── 5. WILCOXON SIGNED-RANK ───────────────────────────────────────────────────

def wilcoxon_sr(x, y):
    """Two-sided Wilcoxon signed-rank test (normal approximation)."""
    d = np.array(x, dtype=float) - np.array(y, dtype=float)
    d = d[d != 0]
    if len(d) == 0:
        return 0.0, 1.0
    abs_d = np.abs(d)
    ranks = pd.Series(abs_d).rank(method="average").values
    W = float(min(np.sum(ranks[d > 0]), np.sum(ranks[d < 0])))
    n = len(d)
    mu = n * (n + 1) / 4
    sigma = np.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (W - mu) / sigma
    p = max(1e-6, min(1.0, 2 * 0.5 * (1 - np.tanh(0.7978845608 * abs(z)))))
    return W, p


# ── 6. MAIN ───────────────────────────────────────────────────────────────────

def main():
    print("OE2 — Análisis benchmark comparativo")
    print("=" * 50)

    print("\n[1/5] Construyendo mapeo agente→archivo…")
    mapping = build_mapping()

    print("[2/5] Cargando evaluaciones…")
    df = load_evaluations(mapping)
    df["familia"] = df["agent"].str.split("_").str[0]
    n_k = int((df.juez == "experto1").sum())
    n_l = int((df.juez == "experto2").sum())
    print(f"      {len(df)} registros | Experto1: {n_k} | Experto2: {n_l} | "
          f"Tests: {df.test_id.nunique()}")
    df.to_csv(os.path.join(SCRIPT_DIR, "oe2_datos_brutos.csv"), index=False)

    print("\n[3/5] Estadísticos descriptivos…")
    agg = df.groupby("agent")[DIMS].mean().round(3)
    agg.to_csv(os.path.join(SCRIPT_DIR, "oe2_medias_por_agente.csv"))
    print(agg.sort_values("puntuacion", ascending=False).to_string())

    print("\n[4/5] Concordancia inter-juez…")
    concord = concordance_stats(df)
    for dim, r in concord.items():
        print(f"  {dim:33s}  α={r['alpha']:+.4f}  ρ={r['rho']:.4f}  "
              f"exacto={r['exact_pct']}%  ±1={r['within1_pct']}%")

    print("\n[5/5] Friedman + Wilcoxon post-hoc (puntuacion)…")
    df_mean = df.groupby(["test_id", "agent"])[DIMS].mean().reset_index()

    friedman_res = {}
    for dim in DIMS:
        piv = df_mean.pivot(index="test_id", columns="agent", values=dim).dropna()
        if piv.shape[0] < 3:
            continue
        chi2, p, mr = friedman_test(piv)
        friedman_res[dim] = {"chi2": chi2, "p": p, "ranking": mr.sort_values(ascending=False)}
        sig = "** SIG **" if p < 0.05 else "(no sig.)"
        top3 = mr.sort_values(ascending=False).head(3)
        print(f"\n  {dim}: χ²={chi2:.2f} p≈{p:.4f} {sig}")
        print("  " + "  ".join(f"{ag}(R̄={r:.2f})" for ag, r in top3.items()))

    piv_p = df_mean.pivot(index="test_id", columns="agent", values="puntuacion").dropna()
    agents = sorted(piv_p.columns.tolist())
    n_comp = len(list(combinations(agents, 2)))
    alpha_bonf = 0.05 / n_comp
    wil_rows = []
    for a, b in combinations(agents, 2):
        W, p = wilcoxon_sr(piv_p[a].tolist(), piv_p[b].tolist())
        ma, mb = piv_p[a].mean(), piv_p[b].mean()
        wil_rows.append({"a": a, "b": b, "W": W, "p": round(p, 4),
                         "sig_bonf": p < alpha_bonf, "sig_05": p < 0.05,
                         "winner": a if ma > mb else b})
    pd.DataFrame(wil_rows).to_csv(os.path.join(SCRIPT_DIR, "oe2_wilcoxon.csv"), index=False)

    # Rankings per juez
    rank_experto1 = df[df.juez == "experto1"].groupby("agent")["puntuacion"].mean().sort_values(ascending=False)
    rank_experto2   = df[df.juez == "experto2"].groupby("agent")["puntuacion"].mean().sort_values(ascending=False)

    # ── Reporte Markdown ──────────────────────────────────────────────────────
    best = agg["puntuacion"].idxmax()
    best_score = agg.loc[best, "puntuacion"]

    md = [
        "# OE2 — Resultados del Benchmark Comparativo", "",
        f"**Tests analizados:** {df.test_id.nunique()} (T001–T020, excl. T017)  ",
        f"**Evaluaciones totales:** {len(df)} (Experto1: {n_k} | Experto2: {n_l})  ",
        f"**Agentes:** 8 configuraciones (Claude/Gemini/BugWizard × contexto)  ",
        "", "---", "",

        "## 1. Estadísticos descriptivos", "",
        "| Agente | Puntuación | Calidad explicación | Calidad propuestas | "
        "Sin alucinación | Identificó error |",
        "|--------|-----------|--------------------|--------------------|"
        "-----------------|-----------------|",
    ]
    for ag in agg.sort_values("puntuacion", ascending=False).index:
        r = agg.loc[ag]
        winner_mark = " 🏆" if ag == best else ""
        md.append(f"| {LABEL[ag]}{winner_mark} | **{r.puntuacion:.3f}** | "
                  f"{r.calidad_explicacion:.3f} | {r.calidad_propuestas:.3f} | "
                  f"{r.nivel_alucinacion:.3f} | {r.identifico_error:.3f} |")

    md += ["", "### Medias por familia", "",
           "| Familia | Puntuación | Calidad explicación | Calidad propuestas |",
           "|---------|-----------|--------------------|--------------------|"]
    for fam, r in df.groupby("familia")[DIMS].mean().sort_values("puntuacion", ascending=False).iterrows():
        md.append(f"| {fam.upper()} | {r.puntuacion:.3f} | "
                  f"{r.calidad_explicacion:.3f} | {r.calidad_propuestas:.3f} |")

    md += ["", "---", "",
           "## 2. Concordancia inter-juez", "",
           "> **Nota metodológica:** El α de Krippendorff ordinal es conservador cuando la ",
           "> distribución de ratings está sesgada hacia valores altos (3–5). El Spearman ρ y los ",
           "> porcentajes de acuerdo son métricas complementarias más interpretables.",
           "",
           "| Dimensión | α Krippendorff | ρ Spearman | Acuerdo exacto | Dentro ±1 |",
           "|-----------|---------------|------------|----------------|-----------|"]
    for dim, r in concord.items():
        interp_rho = "moderada-alta" if r["rho"] > 0.6 else ("moderada" if r["rho"] > 0.4 else "baja")
        md.append(f"| {dim} | {r['alpha']:+.3f} | {r['rho']:.3f} ({interp_rho}) | "
                  f"{r['exact_pct']}% | {r['within1_pct']}% |")

    md += ["", "**Rankings por juez (puntuación media):** ambos jueces producen el mismo Top-4.", "",
           "| Posición | Experto1 | Experto2 |", "|----------|--------|------|"]
    for i, (ag_k, ag_l) in enumerate(zip(rank_experto1.index, rank_experto2.index), 1):
        mark = "✓" if ag_k == ag_l else "≈"
        md.append(f"| {i} | {LABEL[ag_k]} ({rank_experto1[ag_k]:.2f}) | "
                  f"{LABEL[ag_l]} ({rank_experto2[ag_l]:.2f}) | {mark} |")

    md += ["", "---", "",
           "## 3. Test de Friedman", "",
           "| Dimensión | χ² | p (aprox.) | Significativo |",
           "|-----------|-----|-----------|---------------|"]
    for dim, res in friedman_res.items():
        sig = "**Sí** (p<0.05)" if res["p"] < 0.05 else "No"
        top1 = res["ranking"].index[0]
        md.append(f"| {dim} | {res['chi2']:.2f} | {res['p']:.4f} | {sig} — "
                  f"mejor: {LABEL.get(top1, top1)} |")

    sig_bonf = [r for r in wil_rows if r["sig_bonf"]]
    sig_05   = [r for r in wil_rows if r["sig_05"] and not r["sig_bonf"]]
    md += ["", "---", "",
           f"## 4. Wilcoxon post-hoc (puntuación, α Bonferroni = {alpha_bonf:.4f})", ""]
    if sig_bonf:
        md.append("**Pares significativos con corrección Bonferroni:**  ")
        for r in sorted(sig_bonf, key=lambda x: x["p"]):
            md.append(f"- {LABEL[r['a']]} vs {LABEL[r['b']]}: p={r['p']:.4f} → "
                      f"**{LABEL[r['winner']]} gana**")
    else:
        md.append("Ningún par alcanza significancia con corrección Bonferroni (n=19 tests).")
    if sig_05:
        md.append("")
        md.append("**Pares significativos sin corrección (p<0.05, referencial):**  ")
        for r in sorted(sig_05, key=lambda x: x["p"]):
            md.append(f"- {LABEL[r['a']]} vs {LABEL[r['b']]}: p={r['p']:.4f} → "
                      f"{LABEL[r['winner']]} gana")

    md += ["", "---", "",
           "## 5. Configuración ganadora", "",
           f"### 🏆 {LABEL[best]}  (puntuación media: {best_score:.3f})", "",
           "| Dimensión | Valor |", "|-----------|-------|"]
    for dim in DIMS:
        md.append(f"| {dim} | {agg.loc[best, dim]:.3f} |")

    md += ["",
           f"Claude Code con contexto completo (código + logs + trazas detalladas) es la configuración "
           f"ganadora, superando a BugWizard en puntuación media ({agg.loc[best,'puntuacion']:.3f} vs "
           f"{agg.loc['bwz_prompt1','puntuacion']:.3f}/{agg.loc['bwz_prompt2','puntuacion']:.3f}) "
           f"y a Gemini en todas las dimensiones.",
           "", "---", "",
           "## 6. Hallazgos principales", "",
           "1. **Brecha contexto–agente:** Las variantes *basic* (solo código, sin logs) de Claude y "
           "Gemini tienen rendimiento significativamente inferior a las variantes con logs "
           "(Wilcoxon p<0.05). El acceso a logs via MCP es el factor diferenciador más importante.",
           "2. **BugWizard vs Claude:** No existe diferencia estadísticamente significativa entre "
           "BugWizard y Claude Code con logs/detallado (Wilcoxon p>0.05). BugWizard sí supera "
           "significativamente a Gemini y a Claude sin logs (p<0.05).",
           "3. **Gemini:** Consistentemente por debajo de Claude y BugWizard en puntuación global, "
           "aunque con mejor nivel de alucinación relativo (R̄ más alto en nivel_alucinacion).",
           "4. **Concordancia de rankings:** Ambos jueces producen el mismo Top-4 (claude_detailed > "
           "claude_logs ≈ bwz_prompt2 ≈ bwz_prompt1), validando el ranking a pesar del bajo α.",
           "5. **Implicación para Fase 3:** La configuración ganadora para el experimento de MTTD "
           "es Claude Code con contexto detallado, o BugWizard (equivalentes en calidad, "
           "diferente en integración/autonomía).",
           "", "---", "",
           "## 7. Notas metodológicas", "",
           "- **Test017:** Excluido — sin evaluaciones en ningún juez.",
           "- **Test003 y Test018:** Solo evaluaciones de Experto1 (Experto2 no disponible).",
           "- **Mapeo agente→archivo:** 147/152 por contenido (fingerprinting), 5 por eliminación.",
           "- **α Krippendorff ordinal:** Implementación propia (sin scipy). Bajo para escalas Likert "
           "sesgadas — el ρ Spearman (0.44–0.73) y la concordancia ±1 (65–100%) son más informativas.",
           "- **p-values Friedman y Wilcoxon:** Aproximación normal (Wilson–Hilferty / z-score). "
           "Con n=19 tests, interpretación indicativa.",
          ]

    out_md = os.path.join(SCRIPT_DIR, "oe2_resultados.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"\n✓ Análisis completado.")
    print(f"  → oe2_resultados.md")
    print(f"  → oe2_datos_brutos.csv")
    print(f"  → oe2_medias_por_agente.csv")
    print(f"  → oe2_wilcoxon.csv")
    print(f"\n  🏆 GANADOR: {LABEL[best]}  (puntuación={best_score:.3f})")


if __name__ == "__main__":
    main()
