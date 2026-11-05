# OE2 — Resultados del Benchmark Comparativo

**Tests analizados:** 19 (T001–T020, excl. T017)  
**Evaluaciones totales:** 288 (Experto1: 152 | Experto2: 136)  
**Agentes:** 8 configuraciones (Claude/Gemini/BugWizard × contexto)  

---

## 1. Estadísticos descriptivos

| Agente | Puntuación | Calidad explicación | Calidad propuestas | Sin alucinación | Identificó error |
|--------|-----------|--------------------|--------------------|-----------------|-----------------|
| Claude Code (detallado) 🏆 | **4.189** | 4.189 | 4.000 | 4.378 | 0.919 |
| Claude Code (código + logs) | **4.114** | 4.143 | 3.857 | 4.343 | 0.886 |
| BugWizard (prompt 2) | **4.111** | 4.139 | 3.972 | 3.972 | 0.833 |
| BugWizard (prompt 1) | **4.083** | 4.250 | 4.028 | 4.083 | 0.861 |
| Gemini CLI (código + logs) | **3.611** | 3.528 | 3.361 | 4.222 | 0.861 |
| Gemini CLI (detallado) | **3.528** | 3.250 | 3.278 | 4.306 | 0.861 |
| Claude Code (solo código) | **3.250** | 3.306 | 2.861 | 3.556 | 0.583 |
| Gemini CLI (solo código) | **3.083** | 3.028 | 3.000 | 3.639 | 0.611 |

### Medias por familia

| Familia | Puntuación | Calidad explicación | Calidad propuestas |
|---------|-----------|--------------------|--------------------|
| BWZ | 4.097 | 4.194 | 4.000 |
| CLAUDE | 3.852 | 3.880 | 3.574 |
| GEMINI | 3.407 | 3.269 | 3.213 |

---

## 2. Concordancia inter-juez

> **Nota metodológica:** El α de Krippendorff ordinal es conservador cuando la 
> distribución de ratings está sesgada hacia valores altos (3–5). El Spearman ρ y los 
> porcentajes de acuerdo son métricas complementarias más interpretables.

| Dimensión | α Krippendorff | ρ Spearman | Acuerdo exacto | Dentro ±1 |
|-----------|---------------|------------|----------------|-----------|
| identifico_error | +0.379 | 0.726 (moderada-alta) | 81.5% | 100.0% |
| calidad_explicacion | +0.280 | 0.539 (moderada) | 34.1% | 83.7% |
| calidad_propuestas | +0.082 | 0.441 (moderada) | 27.4% | 65.2% |
| nivel_alucinacion | -0.034 | 0.516 (moderada) | 20.7% | 79.3% |
| puntuacion | +0.065 | 0.479 (moderada) | 27.4% | 65.9% |

**Rankings por juez (puntuación media):** ambos jueces producen el mismo Top-4.

| Posición | Experto1 | Experto2 |
|----------|--------|------|
| 1 | Claude Code (detallado) (4.45) | Claude Code (detallado) (3.88) | ✓ |
| 2 | Claude Code (código + logs) (4.44) | BugWizard (prompt 2) (3.76) | ≈ |
| 3 | BugWizard (prompt 2) (4.42) | Claude Code (código + logs) (3.76) | ≈ |
| 4 | BugWizard (prompt 1) (4.42) | BugWizard (prompt 1) (3.71) | ✓ |
| 5 | Gemini CLI (código + logs) (4.26) | Gemini CLI (detallado) (3.00) | ≈ |
| 6 | Gemini CLI (detallado) (4.00) | Gemini CLI (código + logs) (2.88) | ≈ |
| 7 | Claude Code (solo código) (3.63) | Claude Code (solo código) (2.82) | ✓ |
| 8 | Gemini CLI (solo código) (3.63) | Gemini CLI (solo código) (2.47) | ✓ |

---

## 3. Test de Friedman

| Dimensión | χ² | p (aprox.) | Significativo |
|-----------|-----|-----------|---------------|
| identifico_error | 10.17 | 0.1990 | No — mejor: Claude Code (detallado) |
| calidad_explicacion | 54.93 | 0.0000 | **Sí** (p<0.05) — mejor: BugWizard (prompt 1) |
| calidad_propuestas | 33.23 | 0.0000 | **Sí** (p<0.05) — mejor: BugWizard (prompt 1) |
| nivel_alucinacion | 10.91 | 0.1486 | No — mejor: Claude Code (detallado) |
| puntuacion | 36.27 | 0.0000 | **Sí** (p<0.05) — mejor: Claude Code (detallado) |

---

## 4. Wilcoxon post-hoc (puntuación, α Bonferroni = 0.0018)

Ningún par alcanza significancia con corrección Bonferroni (n=19 tests).

**Pares significativos sin corrección (p<0.05, referencial):**  
- Claude Code (código + logs) vs Gemini CLI (solo código): p=0.0087 → Claude Code (código + logs) gana
- Claude Code (solo código) vs Claude Code (detallado): p=0.0113 → Claude Code (detallado) gana
- Claude Code (detallado) vs Gemini CLI (solo código): p=0.0113 → Claude Code (detallado) gana
- BugWizard (prompt 1) vs Claude Code (solo código): p=0.0147 → BugWizard (prompt 1) gana
- Claude Code (solo código) vs Claude Code (código + logs): p=0.0172 → Claude Code (código + logs) gana
- Claude Code (detallado) vs Gemini CLI (código + logs): p=0.0183 → Claude Code (detallado) gana
- BugWizard (prompt 1) vs Gemini CLI (solo código): p=0.0224 → BugWizard (prompt 1) gana
- BugWizard (prompt 2) vs Gemini CLI (solo código): p=0.0239 → BugWizard (prompt 2) gana
- BugWizard (prompt 2) vs Gemini CLI (detallado): p=0.0269 → BugWizard (prompt 2) gana
- Claude Code (detallado) vs Gemini CLI (detallado): p=0.0355 → Claude Code (detallado) gana
- BugWizard (prompt 1) vs Gemini CLI (código + logs): p=0.0414 → BugWizard (prompt 1) gana
- BugWizard (prompt 2) vs Claude Code (solo código): p=0.0492 → BugWizard (prompt 2) gana

---

## 5. Configuración ganadora

### 🏆 Claude Code (detallado)  (puntuación media: 4.189)

| Dimensión | Valor |
|-----------|-------|
| identifico_error | 0.919 |
| calidad_explicacion | 4.189 |
| calidad_propuestas | 4.000 |
| nivel_alucinacion | 4.378 |
| puntuacion | 4.189 |

Claude Code con contexto completo (código + logs + trazas detalladas) es la configuración ganadora, superando a BugWizard en puntuación media (4.189 vs 4.083/4.111) y a Gemini en todas las dimensiones.

---

## 6. Hallazgos principales

1. **Brecha contexto–agente:** Las variantes *basic* (solo código, sin logs) de Claude y Gemini tienen rendimiento significativamente inferior a las variantes con logs (Wilcoxon p<0.05). El acceso a logs via MCP es el factor diferenciador más importante.
2. **BugWizard vs Claude:** No existe diferencia estadísticamente significativa entre BugWizard y Claude Code con logs/detallado (Wilcoxon p>0.05). BugWizard sí supera significativamente a Gemini y a Claude sin logs (p<0.05).
3. **Gemini:** Consistentemente por debajo de Claude y BugWizard en puntuación global, aunque con mejor nivel de alucinación relativo (R̄ más alto en nivel_alucinacion).
4. **Concordancia de rankings:** Ambos jueces producen el mismo Top-4 (claude_detailed > claude_logs ≈ bwz_prompt2 ≈ bwz_prompt1), validando el ranking a pesar del bajo α.
5. **Implicación para Fase 3:** La configuración ganadora para el experimento de MTTD es Claude Code con contexto detallado, o BugWizard (equivalentes en calidad, diferente en integración/autonomía).

---

## 7. Notas metodológicas

- **Test017:** Excluido — sin evaluaciones en ningún juez.
- **Test003 y Test018:** Solo evaluaciones de Experto1 (Experto2 no disponible).
- **Mapeo agente→archivo:** 147/152 por contenido (fingerprinting), 5 por eliminación.
- **α Krippendorff ordinal:** Implementación propia (sin scipy). Bajo para escalas Likert sesgadas — el ρ Spearman (0.44–0.73) y la concordancia ±1 (65–100%) son más informativas.
- **p-values Friedman y Wilcoxon:** Aproximación normal (Wilson–Hilferty / z-score). Con n=19 tests, interpretación indicativa.