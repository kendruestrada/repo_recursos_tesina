**Benchmark:** Evaluación comparativa de agentes de IA para diagnóstico de causa raíz de incidentes de software Reales

**Incidentes evaluados:** 10

**Evaluadores:** Experto1, Experto2

**Configuraciones evaluadas:** 8

**Evaluaciones totales:** 160

---

# Configuración experimental

## Agentes evaluados

| Agente | Contexto disponible |
|---------|---------------------|
| Claude Code (detallado) | Problema + código + logs + explicación del desarrollador + herramientas MCP |
| Claude Code (código + logs) | Problema + código + logs |
| Claude Code (solo código) | Problema + código |
| BugWizard (prompt 2) | Problema + código + logs + explicación del desarrollador + herramientas MCP |
| BugWizard (prompt 1) | Problema + código + logs + herramientas MCP |
| Gemini CLI (detallado) | Problema + código + logs + explicación del desarrollador + herramientas MCP |
| Gemini CLI (código + logs) | Problema + código + logs |
| Gemini CLI (solo código) | Problema + código |

---

# Criterios de evaluación

* Puntuación general (1–5)
* Calidad de la explicación (1–5)
* Calidad de las propuestas (1–5)
* Sin alucinación (1–5)
* Identificó correctamente la causa raíz (Sí / No)

---

# Incidentes evaluados

| ID | Incidente | Complejidad |
|----|-----------|-------------|
| T001 | NullPointerException durante creación de usuario | Baja |
| T002 | Consulta SQL sin índice | Baja |
| T003 | Deadlock entre transacciones | Alta |
| T004 | Error OAuth2 por token expirado | Media |
| T005 | Variables de entorno incorrectas | Alta |
| T006 | Memory Leak en servicio de caché | Muy alta |
| T007 | Error de serialización JSON | Media |
| T008 | Permisos IAM insuficientes sobre S3 | Alta |
| T009 | Validación inconsistente Frontend / Backend | Media |
| T010 | Pérdida de eventos asíncronos | Muy alta |

---

# Evaluaciones

| Incidente | Agente | Juez | Punt. | Exp. | Prop. | Aluc. | Error |
|-----------|--------|------|------:|------:|------:|------:|:------:|
| T001 | Claude Code (detallado) | Experto1 | 5 | 5 | 5 | 5 | Sí |
| T001 | Claude Code (detallado) | Experto2 | 5 | 5 | 5 | 5 | Sí |
| T001 | Claude Code (código + logs) | Experto1 | 5 | 5 | 4 | 5 | Sí |
| T001 | Claude Code (código + logs) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T001 | BugWizard (prompt 2) | Experto1 | 5 | 5 | 4 | 5 | Sí |
| T001 | BugWizard (prompt 2) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T001 | BugWizard (prompt 1) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T001 | BugWizard (prompt 1) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T001 | Gemini CLI (detallado) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T001 | Gemini CLI (detallado) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T001 | Gemini CLI (código + logs) | Experto1 | 4 | 4 | 3 | 5 | Sí |
| T001 | Gemini CLI (código + logs) | Experto2 | 4 | 4 | 3 | 5 | Sí |
| T001 | Claude Code (solo código) | Experto1 | 3 | 3 | 3 | 4 | Sí |
| T001 | Claude Code (solo código) | Experto2 | 3 | 3 | 3 | 4 | Sí |
| T001 | Gemini CLI (solo código) | Experto1 | 3 | 3 | 2 | 4 | No |
| T001 | Gemini CLI (solo código) | Experto2 | 3 | 3 | 3 | 4 | Sí |

| T002 | Claude Code (detallado) | Experto1 | 5 | 5 | 5 | 5 | Sí |
| T002 | Claude Code (detallado) | Experto2 | 4 | 5 | 5 | 5 | Sí |
| T002 | Claude Code (código + logs) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T002 | Claude Code (código + logs) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T002 | BugWizard (prompt 2) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T002 | BugWizard (prompt 2) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T002 | BugWizard (prompt 1) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T002 | BugWizard (prompt 1) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T002 | Gemini CLI (detallado) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T002 | Gemini CLI (detallado) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T002 | Gemini CLI (código + logs) | Experto1 | 4 | 4 | 3 | 5 | Sí |
| T002 | Gemini CLI (código + logs) | Experto2 | 3 | 4 | 3 | 5 | Sí |
| T002 | Claude Code (solo código) | Experto1 | 3 | 3 | 3 | 4 | No |
| T002 | Claude Code (solo código) | Experto2 | 3 | 3 | 3 | 4 | No |
| T002 | Gemini CLI (solo código) | Experto1 | 2 | 3 | 2 | 4 | No |
| T002 | Gemini CLI (solo código) | Experto2 | 3 | 3 | 2 | 4 | No |

| T003 | Claude Code (detallado) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T003 | Claude Code (detallado) | Experto2 | 5 | 5 | 4 | 5 | Sí |
| T003 | Claude Code (código + logs) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T003 | Claude Code (código + logs) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T003 | BugWizard (prompt 2) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T003 | BugWizard (prompt 2) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T003 | BugWizard (prompt 1) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T003 | BugWizard (prompt 1) | Experto2 | 3 | 4 | 4 | 5 | Sí |
| T003 | Gemini CLI (detallado) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T003 | Gemini CLI (detallado) | Experto2 | 3 | 4 | 4 | 5 | No |
| T003 | Gemini CLI (código + logs) | Experto1 | 3 | 4 | 3 | 5 | No |
| T003 | Gemini CLI (código + logs) | Experto2 | 3 | 4 | 3 | 5 | No |
| T003 | Claude Code (solo código) | Experto1 | 2 | 3 | 2 | 4 | No |
| T003 | Claude Code (solo código) | Experto2 | 3 | 3 | 2 | 4 | No |
| T003 | Gemini CLI (solo código) | Experto1 | 2 | 2 | 2 | 4 | No |
| T003 | Gemini CLI (solo código) | Experto2 | 2 | 2 | 2 | 4 | No |

| T004 | Claude Code (detallado) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T004 | Claude Code (detallado) | Experto2 | 5 | 5 | 5 | 5 | Sí |
| T004 | Claude Code (código + logs) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T004 | Claude Code (código + logs) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T004 | BugWizard (prompt 2) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T004 | BugWizard (prompt 2) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T004 | BugWizard (prompt 1) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T004 | BugWizard (prompt 1) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T004 | Gemini CLI (detallado) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T004 | Gemini CLI (detallado) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T004 | Gemini CLI (código + logs) | Experto1 | 4 | 4 | 3 | 5 | Sí |
| T004 | Gemini CLI (código + logs) | Experto2 | 3 | 4 | 3 | 5 | Sí |
| T004 | Claude Code (solo código) | Experto1 | 3 | 3 | 3 | 4 | No |
| T004 | Claude Code (solo código) | Experto2 | 3 | 3 | 3 | 4 | Sí |
| T004 | Gemini CLI (solo código) | Experto1 | 3 | 3 | 2 | 4 | No |
| T004 | Gemini CLI (solo código) | Experto2 | 2 | 3 | 2 | 4 | No |

| T005 | Claude Code (detallado) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T005 | Claude Code (detallado) | Experto2 | 4 | 5 | 5 | 5 | Sí |
| T005 | Claude Code (código + logs) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T005 | Claude Code (código + logs) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T005 | BugWizard (prompt 2) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T005 | BugWizard (prompt 2) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T005 | BugWizard (prompt 1) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T005 | BugWizard (prompt 1) | Experto2 | 3 | 4 | 4 | 5 | Sí |
| T005 | Gemini CLI (detallado) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T005 | Gemini CLI (detallado) | Experto2 | 3 | 4 | 4 | 5 | No |
| T005 | Gemini CLI (código + logs) | Experto1 | 3 | 4 | 3 | 5 | No |
| T005 | Gemini CLI (código + logs) | Experto2 | 3 | 4 | 3 | 5 | No |
| T005 | Claude Code (solo código) | Experto1 | 2 | 3 | 2 | 4 | No |
| T005 | Claude Code (solo código) | Experto2 | 2 | 3 | 2 | 4 | No |
| T005 | Gemini CLI (solo código) | Experto1 | 2 | 2 | 2 | 4 | No |
| T005 | Gemini CLI (solo código) | Experto2 | 2 | 2 | 2 | 4 | No |

| T006 | Claude Code (detallado) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T006 | Claude Code (detallado) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T006 | Claude Code (código + logs) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T006 | Claude Code (código + logs) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T006 | BugWizard (prompt 2) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T006 | BugWizard (prompt 2) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T006 | BugWizard (prompt 1) | Experto1 | 3 | 4 | 3 | 5 | Sí |
| T006 | BugWizard (prompt 1) | Experto2 | 4 | 4 | 3 | 5 | Sí |
| T006 | Gemini CLI (detallado) | Experto1 | 3 | 4 | 4 | 5 | No |
| T006 | Gemini CLI (detallado) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T006 | Gemini CLI (código + logs) | Experto1 | 3 | 3 | 3 | 5 | No |
| T006 | Gemini CLI (código + logs) | Experto2 | 3 | 3 | 3 | 5 | No |
| T006 | Claude Code (solo código) | Experto1 | 2 | 3 | 2 | 4 | No |
| T006 | Claude Code (solo código) | Experto2 | 2 | 3 | 2 | 4 | No |
| T006 | Gemini CLI (solo código) | Experto1 | 2 | 2 | 2 | 4 | No |
| T006 | Gemini CLI (solo código) | Experto2 | 2 | 2 | 2 | 4 | No |

| T007 | Claude Code (detallado) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T007 | Claude Code (detallado) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T007 | Claude Code (código + logs) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T007 | Claude Code (código + logs) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T007 | BugWizard (prompt 2) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T007 | BugWizard (prompt 2) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T007 | BugWizard (prompt 1) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T007 | BugWizard (prompt 1) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T007 | Gemini CLI (detallado) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T007 | Gemini CLI (detallado) | Experto2 | 3 | 4 | 4 | 5 | Sí |
| T007 | Gemini CLI (código + logs) | Experto1 | 3 | 4 | 3 | 5 | Sí |
| T007 | Gemini CLI (código + logs) | Experto2 | 3 | 4 | 3 | 5 | Sí |
| T007 | Claude Code (solo código) | Experto1 | 3 | 3 | 3 | 4 | Sí |
| T007 | Claude Code (solo código) | Experto2 | 3 | 3 | 3 | 4 | Sí |
| T007 | Gemini CLI (solo código) | Experto1 | 3 | 3 | 2 | 4 | No |
| T007 | Gemini CLI (solo código) | Experto2 | 3 | 3 | 2 | 4 | No |

| T008 | Claude Code (detallado) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T008 | Claude Code (detallado) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T008 | Claude Code (código + logs) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T008 | Claude Code (código + logs) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T008 | BugWizard (prompt 2) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T008 | BugWizard (prompt 2) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T008 | BugWizard (prompt 1) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T008 | BugWizard (prompt 1) | Experto2 | 3 | 4 | 4 | 5 | Sí |
| T008 | Gemini CLI (detallado) | Experto1 | 3 | 4 | 4 | 5 | No |
| T008 | Gemini CLI (detallado) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T008 | Gemini CLI (código + logs) | Experto1 | 3 | 4 | 3 | 5 | No |
| T008 | Gemini CLI (código + logs) | Experto2 | 3 | 4 | 3 | 5 | No |
| T008 | Claude Code (solo código) | Experto1 | 2 | 3 | 2 | 4 | No |
| T008 | Claude Code (solo código) | Experto2 | 2 | 3 | 2 | 4 | No |
| T008 | Gemini CLI (solo código) | Experto1 | 2 | 2 | 2 | 4 | No |
| T008 | Gemini CLI (solo código) | Experto2 | 2 | 2 | 2 | 4 | No |

| T009 | Claude Code (detallado) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T009 | Claude Code (detallado) | Experto2 | 4 | 5 | 5 | 5 | Sí |
| T009 | Claude Code (código + logs) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T009 | Claude Code (código + logs) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T009 | BugWizard (prompt 2) | Experto1 | 4 | 5 | 4 | 5 | Sí |
| T009 | BugWizard (prompt 2) | Experto2 | 4 | 5 | 4 | 5 | Sí |
| T009 | BugWizard (prompt 1) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T009 | BugWizard (prompt 1) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T009 | Gemini CLI (detallado) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T009 | Gemini CLI (detallado) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T009 | Gemini CLI (código + logs) | Experto1 | 3 | 4 | 3 | 5 | Sí |
| T009 | Gemini CLI (código + logs) | Experto2 | 3 | 4 | 3 | 5 | No |
| T009 | Claude Code (solo código) | Experto1 | 3 | 3 | 3 | 4 | Sí |
| T009 | Claude Code (solo código) | Experto2 | 2 | 3 | 3 | 4 | No |
| T009 | Gemini CLI (solo código) | Experto1 | 2 | 3 | 2 | 4 | No |
| T009 | Gemini CLI (solo código) | Experto2 | 2 | 3 | 2 | 4 | No |

| T010 | Claude Code (detallado) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T010 | Claude Code (detallado) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T010 | Claude Code (código + logs) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T010 | Claude Code (código + logs) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T010 | BugWizard (prompt 2) | Experto1 | 4 | 4 | 4 | 5 | Sí |
| T010 | BugWizard (prompt 2) | Experto2 | 4 | 4 | 4 | 5 | Sí |
| T010 | BugWizard (prompt 1) | Experto1 | 3 | 4 | 3 | 5 | Sí |
| T010 | BugWizard (prompt 1) | Experto2 | 3 | 4 | 3 | 5 | Sí |
| T010 | Gemini CLI (detallado) | Experto1 | 3 | 4 | 4 | 5 | No |
| T010 | Gemini CLI (detallado) | Experto2 | 3 | 4 | 4 | 5 | No |
| T010 | Gemini CLI (código + logs) | Experto1 | 3 | 3 | 3 | 5 | No |
| T010 | Gemini CLI (código + logs) | Experto2 | 3 | 3 | 3 | 5 | No |
| T010 | Claude Code (solo código) | Experto1 | 2 | 3 | 2 | 4 | No |
| T010 | Claude Code (solo código) | Experto2 | 2 | 3 | 2 | 4 | No |
| T010 | Gemini CLI (solo código) | Experto1 | 2 | 2 | 2 | 4 | No |
| T010 | Gemini CLI (solo código) | Experto2 | 2 | 2 | 2 | 4 | No |

---
## Estadísticos descriptivos

| Agente | Puntuación | Calidad explicación | Calidad propuestas | Sin alucinación | Identificó error |
|:-------|-----------:|--------------------:|-------------------:|----------------:|-----------------:|
| **Claude Code (detallado)** 🏆 | **4.25** | **4.85** | **4.45** | **5.00** | **1.000** |
| **Claude Code (código + logs)** | **3.95** | **4.60** | **3.95** | **5.00** | **1.000** |
| **BugWizard (prompt 2)** | **4.05** | **4.65** | **4.00** | **5.00** | **1.000** |
| **BugWizard (prompt 1)** | **3.70** | **4.05** | **3.80** | **5.00** | **1.000** |
| **Gemini CLI (detallado)** | **3.65** | **4.00** | **4.00** | **5.00** | **0.750** |
| **Gemini CLI (código + logs)** | **3.30** | **3.65** | **3.05** | **5.00** | **0.400** |
| **Claude Code (solo código)** | **2.55** | **3.00** | **2.55** | **4.00** | **0.400** |
| **Gemini CLI (solo código)** | **2.45** | **2.55** | **2.15** | **4.00** | **0.100** |

```


