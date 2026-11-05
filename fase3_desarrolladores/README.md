# Fase 3: experimento con desarrolladores

Corresponde a la sección 4.4 y al Anexo D de la tesina.

Cuatro desarrolladores de Apside (D1 a D4) resolvieron 16 tickets basados en los escenarios sintéticos de
la Fase 1. Cada uno resolvió algunos tickets con BugWizard y el resto con su flujo habitual, que incluía
la consola de AWS y asistentes de IA genéricos. Los grupos D1–D2 y D3–D4 tuvieron asignaciones opuestas,
de modo que cada ticket se resolvió dos veces en cada condición.

## Contenido

| Ruta | Qué hay |
|---|---|
| `tickets/` | Los 16 tickets entregados a los participantes: síntoma y comportamiento esperado, sin la causa raíz. |
| `resultados/resultados_D1.md` … `resultados_D4.md` | Registro de cada desarrollador: método, horas, minutos, causa raíz declarada, archivo y notas. |
| `resultados/plantilla.md` | Plantilla entregada a los participantes. |
| `protocolo_experimento_OE4.md`, `hoja_registro_MTTD.csv` | Protocolo y hoja de registro preparados antes del experimento. |
| `NOTAS_DE_TRABAJO.md` | Notas de preparación del material. |

**Nota:** el protocolo planteaba dos desarrolladores con bloques de tickets. El diseño que finalmente se
ejecutó (4 desarrolladores, los 16 tickets cada uno, en grupos cruzados) es el que describe la tesina.

La clasificación de cada respuesta como correcta o parcial se hizo comparándola con la causa raíz de
`../fase1_banco_interno/especificaciones_y_ejecucion/test_0XX/especificacion_test_0XX.txt`. El resultado
está en la Tabla D.1 de la tesina.
