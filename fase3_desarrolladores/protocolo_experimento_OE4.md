# Protocolo del Experimento OE4 — MTTD con y sin BugWizard

**Objetivo:** validar H1 (reducción de MTTD ≥30% al usar la herramienta ganadora, integrada en
el flujo de trabajo habitual del desarrollador) mediante un experimento controlado, cronometrado,
con desarrolladores reales de Apside.

**Estado de este documento:** borrador de trabajo para T4.1/T4.2 de la planificación. Contiene
decisiones ya tomadas y pendientes marcados explícitamente como `[PENDIENTE]`.

---

## 1. Diseño experimental

Diseño **cruzado (crossover) 2×2**, dentro-sujeto, con **dos desarrolladores**:

- **Factor tratamiento:** con BugWizard / sin BugWizard (stack habitual del dev).
- **Factor período:** Sesión 1 / Sesión 2.
- En vez de repetir los mismos ítems en ambas condiciones (lo que contaminaría el MTTD por
  aprendizaje/memoria), se usan **dos bloques de ítems distintos pero equivalentes en dificultad**
  (Bloque A y Bloque B, ver sección 3). Cada bloque se resuelve una vez con la herramienta y una
  vez sin ella, por desarrolladores distintos, lo que permite construir pares para el análisis
  pareado (ver sección 8) sin que ningún desarrollador vea el mismo bug dos veces.

| | Sesión 1 | Sesión 2 |
|---|---|---|
| **Dev 1** | Bloque A — **SIN** BugWizard | Bloque B — **CON** BugWizard |
| **Dev 2** | Bloque A — **CON** BugWizard | Bloque B — **SIN** BugWizard |

- El orden de la condición (cuál va primero) queda contrabalanceado entre los dos devs, controlando
  el efecto de aprendizaje/fatiga entre sesiones.
- Cada bloque se resuelve completo por los dos devs en la misma sesión (en paralelo, cada uno en su
  propio ambiente/ticket), así que un eventual efecto de práctica entre sesión 1 y sesión 2 afecta
  a ambas condiciones por igual dentro del bloque B, y no sesga la comparación con/sin herramienta.
- Se recomienda dejar al menos algunas horas (idealmente 1 día) entre sesión 1 y sesión 2 por
  desarrollador, para reducir fatiga.

**Importante:** los devs que participen deben ser distintos de quienes construyeron/evaluaron
BugWizard (Experto1, Experto2) y no deben haber visto antes estos escenarios — confirmado por el usuario
como condición del diseño.

---

## 2. Checklist previo a fijar fecha `[PENDIENTE — bloqueante]`

- [ ] Verificar en AWS qué stacks de `codigo_evaluado_en_test/bw_test_XXX` siguen desplegados.
- [ ] Verificar que las canarias (`synthetics-canaries`, cron) siguen generando tráfico/logs para
      reproducir cada bug en vivo.
- [ ] Re-desplegar y re-disparar las canarias de los ítems que se vayan a usar (ideal: 24-48h antes
      de la sesión, para tener logs "frescos" y realistas en CloudWatch).
- [ ] Confirmar que BugWizard y el MCP de CloudWatch (`cw-mcp-server`) apuntan al mismo perfil/cuenta
      AWS donde están desplegados estos tests.
- [ ] Para la condición "sin BugWizard": confirmar qué herramientas tendrá el dev (¿acceso a
      consola AWS/CloudWatch manualmente? ¿solo el código? esto debe reflejar su flujo *habitual*,
      no una versión artificialmente empobrecida — ver sección 5).
- [ ] Reclutar y agendar a los 2 desarrolladores, con al menos un bloque de tiempo continuo por
      sesión (ver estimación de duración en sección 4).

No fijar fecha con los desarrolladores hasta resolver estos puntos — si algún ambiente no puede
revivirse, hay que reemplazar ese ítem por uno de la reserva (sección 3.3) del mismo nivel de
dificultad.

---

## 3. Pool de ítems

### 3.1 Los 16 tests utilizables

De los 19 tests sintéticos evaluados en OE2 (test_001 a test_020, excluyendo test_017), **3 quedan
fuera** (test_001, 002, 003) porque no tienen código en `codigo_evaluado_en_test` — solo la
especificación en texto. No se pueden usar en una sesión donde el dev debe leer/depurar código real.

La columna "dificultad estimada" usa como proxy la tasa de identificación correcta de la causa raíz
por los 8 agentes evaluados en OE2 (`oe2_datos_brutos.csv`, campo `identifico_error`): una tasa baja
sugiere un bug más difícil de diagnosticar incluso para agentes con acceso a logs.

| ID | Título (síntoma) | Tasa histórica identificó causa (OE2) | Dificultad estimada | Tipo de falla |
|----|---|---:|---|---|
| bw_test_004 | Suscripción activa sin acceso a funciones premium | 0.62 | Alta | Falla asíncrona (DynamoDB Stream → Cognito) |
| bw_test_011 | Emails de confirmación de compra duplicados | 0.44 | Alta | Idempotencia / colas (SQS) |
| bw_test_014 | Puntos de fidelidad registrados incorrectamente | 0.69 | Media | Idempotencia / eventos (EventBridge) |
| bw_test_005 | Solicitudes de crédito atascadas en 'en proceso' | 0.75 | Media | Dependencia síncrona circular + throttling |
| bw_test_010 | Nombres con tildes se muestran truncados | 0.75 | Media | Bug de encoding (dato silencioso) |
| bw_test_019 | Búsquedas lentas en una categoría de productos | 0.75 | Media | Hot partition (DynamoDB) |
| bw_test_008 | Transferencias entre cuentas: el dinero 'desaparece' | 0.81 | Media | Consistencia eventual |
| bw_test_007 | Aplicación completamente caída | 0.88 | Media | Cascading failure / circuit breaker mal configurado |
| bw_test_009 | Degradación de rendimiento tras varias horas de uso | 0.94 | Baja | Memory leak / reuso de contenedor Lambda |
| bw_test_016 | Transferencias bancarias bloqueadas indefinidamente | 0.94 | Baja | Deadlock distribuido |
| bw_test_020 | Posible fuga de datos de sesión desde sitios externos | 0.94 | Baja | Seguridad (CORS mal configurado) |
| bw_test_006 | Compras rechazadas por error de 'precio manipulado' | 1.00 | Baja | Invalidación de caché |
| bw_test_012 | Inventario del producto muestra stock negativo | 1.00 | Baja | Race condition / lost update |
| bw_test_013 | Timeouts aleatorios después de varios minutos de uso | 1.00 | Baja | Agotamiento de connection pool |
| bw_test_015 | Eliminación accidental de fotos de la galería | 1.00 | Baja | Bug de código (prefix S3 incorrecto) |
| bw_test_018 | Orden 'completada' de forma inconsistente | 1.00 | Baja | Orquestación Saga / compensación fallida |

(2 Alta, 6 Media, 8 Baja.)

### 3.2 Asignación a bloques

**Opción completa (12 ítems, 6 por bloque):**

| Bloque A (6) | Nivel | Bloque B (6) | Nivel |
|---|---|---|---|
| bw_test_004 | Alta | bw_test_011 | Alta |
| bw_test_005 | Media | bw_test_007 | Media |
| bw_test_019 | Media | bw_test_008 | Media |
| bw_test_009 | Baja | bw_test_012 | Baja |
| bw_test_015 | Baja | bw_test_016 | Baja |
| bw_test_018 | Baja | bw_test_020 | Baja |

Cada bloque queda con 1 ítem Alta, 2 Media, 3 Baja — balanceado.

**Opción reducida (8 ítems, 4 por bloque, subconjunto anidado de la anterior)** — recomendada si
solo se dispone de una jornada por desarrollador:

| Bloque A' (4) | Nivel | Bloque B' (4) | Nivel |
|---|---|---|---|
| bw_test_004 | Alta | bw_test_011 | Alta |
| bw_test_019 | Media | bw_test_007 | Media |
| bw_test_009 | Baja | bw_test_012 | Baja |
| bw_test_018 | Baja | bw_test_020 | Baja |

Se puede empezar con la opción reducida y, si sobra tiempo en la sesión, sumar los 2 ítems
restantes de cada bloque (extiende a la opción completa sin romper el balance).

### 3.3 Reserva (4 ítems, para reemplazo si un ambiente AWS no puede revivirse)

| ID | Nivel | Reemplaza en caso de baja de |
|---|---|---|
| bw_test_014 | Media | bw_test_005, 019, 007 u 008 |
| bw_test_006 | Baja | bw_test_009, 015, 018, 012, 016 o 020 |
| bw_test_010 | Media | idem anterior |
| bw_test_013 | Baja | idem anterior |

`[PENDIENTE]` decidir opción completa (12) vs reducida (8) según disponibilidad real de tiempo de
los 2 desarrolladores — no se fija aquí porque es una decisión logística, no metodológica.

---

## 4. Estimación de duración por sesión

Tiempos máximos sugeridos por ítem antes de declarar timeout (ver sección 6):

| Nivel | Tiempo máximo sugerido |
|---|---|
| Alta | 40 min |
| Media | 25 min |
| Baja | 15 min |

Bloque completo (6 ítems: 1 Alta + 2 Media + 3 Baja): ≈ 40 + 50 + 45 = **135 min máx.** por
desarrollador (más corto en la práctica, esto es cota superior). Bloque reducido (4 ítems):
≈ 40+25+15+15 = **95 min máx.**

Sumar 10-15 min de briefing inicial y 5-10 min de entrevista post-sesión (sección 7).

---

## 5. Materiales por condición

**Ambas condiciones reciben:**
- El ticket del ítem (`tickets/ticket_bw_test_XXX.md`) — reporte tipo soporte, sin causa raíz.
- Acceso de solo lectura al repositorio de código (`codigo_evaluado_en_test/bw_test_XXX/`).
- Acceso a la consola/CLI de AWS del ambiente donde corre ese test (CloudWatch Logs, DynamoDB,
  etc.) — porque así es como un desarrollador de Apside diagnosticaría un incidente hoy, con o sin
  agente. Quitarle el acceso a logs en la condición "sin BugWizard" sesgaría el experimento a favor
  de la herramienta (no estaría midiendo el aporte de BugWizard, sino el de tener logs o no).

**Condición CON BugWizard, además:**
- BugWizard configurado y funcionando contra el MCP de CloudWatch del ambiente correspondiente.

**Condición SIN BugWizard:**
- El desarrollador usa su flujo habitual (IDE, consola AWS, `grep`/CLI, o incluso Claude Code /
  Gemini CLI genéricos si eso es lo que usaría normalmente) — **sin** BugWizard. Esto es lo que se
  compara contra "con BugWizard" para medir el efecto de la herramienta específica, no el efecto de
  "usar IA" en general (eso ya se midió indirectamente en OE2 con las 8 configuraciones).

`[PENDIENTE]` confirmar con cada dev, antes de su sesión "sin BugWizard", qué herramientas usa
normalmente, para que la condición control sea realista y no un "sin ayuda alguna" artificial.

---

## 6. Protocolo de sesión (paso a paso)

1. **Briefing (no revelar la hipótesis):** explicar que se está evaluando cómo los desarrolladores
   diagnostican incidentes en distintos escenarios, sin mencionar que se espera una reducción de
   30% ni cuál condición es la "buena". Firmar consentimiento informado.
2. Entregar el ticket del primer ítem del bloque asignado.
3. Iniciar el cronómetro apenas el desarrollador empieza a trabajar en el ticket.
4. El desarrollador investiga libremente (código, logs, BugWizard si corresponde) hasta que:
   - **(a)** declara la causa raíz — se detiene el cronómetro y se registra su respuesta, o
   - **(b)** se cumple el tiempo máximo del ítem (tabla sección 4) — se marca como *timeout*, se
     registra qué había encontrado hasta ese momento (si algo) y se pasa al siguiente ítem.
5. El facilitador no da pistas ni confirma/corrige hipótesis intermedias del desarrollador — solo
   cronometra y registra.
6. Registrar cada ítem en la hoja de datos (`hoja_registro_MTTD.csv`, sección 8).
7. Repetir 2-6 para cada ítem del bloque.
8. Al terminar el bloque, breve descanso, y entrevista corta (sección 7).

**Criterio de "causa raíz identificada correctamente":** se compara la respuesta del desarrollador
contra la sección "Causa Raíz" de `especificacion_test_XXX.txt` (documento que el facilitador SÍ
puede ver, el desarrollador no). Registrar como Sí / Parcial / No — igual que el criterio usado en
OE2, para poder comparar precisión entre fases.

---

## 7. Guion de entrevista post-sesión (5-10 min por desarrollador, al final de cada sesión)

1. ¿Cómo describirías tu proceso para encontrar la causa raíz en estos casos?
2. (Solo si tuvo la condición con BugWizard) ¿En qué momentos sentiste que la herramienta te ayudó
   más? ¿Hubo momentos en que te generó ruido o desconfianza (posibles alucinaciones)?
3. ¿Hubo algún ítem donde te hubiera gustado tener más información de la que traía el ticket?
4. ¿Usarías esta herramienta en tu trabajo diario? ¿Por qué?

No revelar en ningún momento (ni antes ni durante) que se está midiendo específicamente una
reducción de tiempo del 30%.

---

## 8. Hoja de registro y plan de análisis

Ver `hoja_registro_MTTD.csv` (plantilla) — una fila por (desarrollador, ítem).

**Análisis estadístico (según `tema.txt`, sección 3.3):**
- Unidad de comparación pareada: **el ítem**. Cada ítem del pool se resuelve una vez con BugWizard
  y una vez sin él (por desarrolladores distintos) → con 12 ítems (opción completa) se obtienen 12
  pares (con 8 ítems, 8 pares) para el test de Wilcoxon signed-rank.
- Wilcoxon signed-rank pareado sobre MTTD (con vs. sin BugWizard).
- Bootstrap para intervalo de confianza de la reducción porcentual de MTTD.
- Contrastar contra H1 (reducción ≥30%).
- Comparar también precisión de causa raíz (Sí/Parcial/No) entre condiciones.
- Análisis cualitativo de las entrevistas (sección 7) y de los ítems con timeout.

---

## 9. Amenazas a la validez (para la sección correspondiente del informe)

- **Tamaño muestral muy pequeño (n=2 desarrolladores):** cualquier resultado cuantitativo debe
  presentarse como indicativo/exploratorio, no concluyente; el n real para el Wilcoxon son los
  pares por ítem (8-12), que sigue siendo bajo para el estándar de la literatura pero es lo
  disponible dado el contexto real de Apside (recursos y tiempo de los desarrolladores).
- **Ítems provenientes del mismo banco usado en OE2:** aunque los 2 desarrolladores del experimento
  no participaron en la construcción ni evaluación de BugWizard y no vieron antes estos escenarios
  (confirmado), el diseño de los bugs sigue siendo obra de una sola persona (el investigador), lo
  que puede introducir sesgos sistemáticos no capturados por la estratificación de dificultad usada
  aquí (proxy basado en tasa de acierto de agentes, no en una medición humana de dificultad).
  ConDefects se descartó como fuente para este experimento por incompatibilidad de constructo
  (bugs algorítmicos sin logs/telemetría, ver nota en README de esta carpeta).
  `[PENDIENTE]` — 3 de los 19 tests sintéticos (001-003) no tienen código recuperado; si aparece el
  repositorio original convendría incorporarlos al pool para ampliar la reserva.
- **Efecto de la persona, no solo de la herramienta:** con solo 2 desarrolladores, diferencias de
  seniority/familiaridad con AWS entre ambos pueden confundirse con el efecto del bloque o la
  sesión; el diseño cruzado mitiga esto (cada dev pasa por ambas condiciones) pero no lo elimina
  del todo dado que cada dev solo ve un bloque por condición.
- **Realismo del ambiente:** los tests corren en stacks de prueba dedicados, no en producción real
  de un cliente; la carga, escala y ruido de logs son menores que en un incidente real de Apside.
