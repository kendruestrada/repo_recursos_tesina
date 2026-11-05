# Recursos de la tesina: agentes basados en LLM para el diagnóstico de incidentes

Material de apoyo de la tesina *"Agentes autónomos basados en LLMs para el diagnóstico de incidentes en
sistemas distribuidos: evaluación empírica comparativa y efecto del acceso a código y observabilidad"*
(Magíster en Tecnologías de la Información, Universidad Técnica Federico Santa María, 2026).

Este repositorio reúne los escenarios de prueba, los scripts de ejecución, las respuestas de los agentes,
las evaluaciones y los scripts de análisis. Con ellos se puede revisar o reproducir lo que reporta el
informe. La tesina compara **BugWizard**, un agente desarrollado en Apside basado en RAG, con
**Claude Code** y **Gemini CLI**, en tres fases.

| Fase | Qué se evaluó | Carpeta | Sección de la tesina |
|---|---|---|---|
| 1 | Evaluación ciega por dos expertos de 8 configuraciones sobre 19 escenarios sintéticos y 10 incidentes reales | [`fase1_banco_interno/`](fase1_banco_interno/) | 4.2 y Anexos A–B |
| 2 | Localización de fallas en 36 programas del dataset público ConDefects | [`fase2_condefects/`](fase2_condefects/) | 4.3 y Anexo C |
| 3 | Experimento cronometrado con 4 desarrolladores, con y sin BugWizard | [`fase3_desarrolladores/`](fase3_desarrolladores/) | 4.4 y Anexo D |

## Qué se puede reproducir sin acceso a AWS

- **Resultados de la Fase 1.** `fase1_banco_interno/analisis/oe2_analisis.py` vuelve a calcular las medias,
  Friedman, Wilcoxon y la concordancia entre jueces a partir de las notas de los expertos (requiere `pandas`
  y `numpy`).
- **Resultados de la Fase 2.** `fase2_condefects/condefects-eval/score.py` vuelve a puntuar las predicciones
  guardadas de los cuatro sistemas (requiere clonar ConDefects; ver el README de la fase).
- **Resultados de la Fase 3.** Los registros de cada desarrollador están en `fase3_desarrolladores/resultados/`.

Para volver a ejecutar los agentes hay que desplegar los escenarios en una cuenta propia de AWS y tener
acceso a los modelos (Bedrock para Claude y la API de Google para Gemini). Además, la plataforma
BugWizard no es pública: los *runners* incluidos muestran cómo se invocó, pero necesitan una instancia del
backend.

## Anonimización

Para publicar el material se aplicaron estos cambios a la copia de trabajo original:

- Los identificadores de cuentas AWS se reemplazaron por `123456789012`, y los endpoints de API Gateway por
  `xxxxxxxxxx.execute-api...`. Los tokens y las credenciales se reemplazaron por `<JWT_REDACTADO>` o
  `<REDACTADO>`, y los dominios internos y repositorios privados por `example.com`.
- Los jueces de la Fase 1 aparecen como `experto1` (el autor) y `experto2` (otro ingeniero de Apside).
- Los desarrolladores de la Fase 3 aparecen como `D1` a `D4`, igual que en la tesina.
- Los diez incidentes reales de clientes solo se incluyen como títulos y calificaciones. Su código, sus
  logs y las respuestas de los agentes son confidenciales.

Por esto, algunos scripts de despliegue necesitan que se completen los valores propios (perfil de AWS,
cuenta, URLs) antes de usarlos.

## Modelos usados

| Fase | Fecha | BugWizard y Claude Code | Gemini |
|---|---|---|---|
| 1 | febrero de 2026 | Claude Sonnet 4 (Bedrock) | gemini-2.5-flash |
| 2 | julio a septiembre de 2026 | Claude Sonnet 5 (Bedrock) | gemini-3.5-flash |
| 3 | 2026 (después de la Fase 2) | Claude Sonnet 5 (Bedrock), solo BugWizard | — |

## Autor

Experto1 Estrada Rodríguez. Profesor guía: Ricardo Ñanculef, Iván Pizarro.
