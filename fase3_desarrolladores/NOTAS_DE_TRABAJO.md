# Material del experimento OE4 (MTTD con/sin BugWizard)

Generado a partir de los 19 tests sintéticos de OE2 (excluyendo test_001-003 por falta de código, y
test_017 ya excluido desde OE2). ConDefects se dejó fuera del experimento principal por no compartir
el mismo constructo (bugs algorítmicos sin logs ni sistema distribuido, no representativos de lo que
BugWizard está diseñado para diagnosticar).

- `protocolo_experimento_OE4.md` — protocolo completo: diseño, checklist previo, pool de ítems,
  asignación a bloques, duración estimada, materiales, guion de sesión y de entrevista, plan de
  análisis y amenazas a la validez. **Léelo primero.**
- `hoja_registro_MTTD.csv` — plantilla de registro de datos para llenar durante las sesiones
  (opción completa de 12 ítems; si se usa la opción reducida de 8, basta con borrar las filas de
  bw_test_014-hoja no aplica, ver sección 3.2 del protocolo — usar solo los 4 ítems por bloque
  indicados ahí).
- `tickets/` — 16 fichas de incidente (una por test utilizable), redactadas a partir de la sección
  "Preguntas" de cada especificación original: **no incluyen la causa raíz ni el análisis interno**,
  solo el síntoma reportado y el comportamiento esperado, como llegaría un ticket real. Son las que
  se entregan a los desarrolladores. Las especificaciones completas (con causa raíz) siguen en
  `codigo_evaluado_en_test/tests-bugwizard/test_XXX/especificacion_test_XXX.txt` — el facilitador
  las usa para calificar la respuesta del desarrollador, pero NUNCA se muestran al participante.

Pendiente antes de agendar a los desarrolladores: confirmar que los ambientes AWS de los ítems
elegidos siguen desplegados y generando logs (sección 2 del protocolo).
