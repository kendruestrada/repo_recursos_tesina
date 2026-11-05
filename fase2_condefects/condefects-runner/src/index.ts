import * as path from 'path';
import * as fs from 'fs';

import { ProjectsSocketClient } from './projects.socket';
import { ConversationsSocketClient } from './conversations.socket';
import { MessagesSocketClient } from './messages.socket';
import {
  readManifest,
  buildRepositoryZipBase64,
  savePrediction,
  predictionExists,
  fetchExistingProjectsByName,
} from './util';

// ---- Config por entorno ----
const BACKEND_URL = process.env.BACKEND_URL!;
const BACKEND_WS_URL = process.env.BACKEND_WS_URL!;
const TOKEN = process.env.BACKEND_TOKEN!;
const CHECKOUT_DIR = process.env.CHECKOUT_DIR!;          // dir del checkout / Code de ConDefects
const MANIFEST = process.env.MANIFEST ?? 'manifest.csv'; // generado por build_manifest.py
const PREDICTIONS_DIR = process.env.PREDICTIONS_DIR ?? 'predictions';
const LIMIT = process.env.LIMIT ? parseInt(process.env.LIMIT, 10) : Infinity;
// Carpeta con logs reales por programa (<program_key>.log), generados p. ej.
// con condefects-eval/generate_test_logs.py. Si existe un archivo para el
// programa, se usa ese contenido en vez de LOG_TEXT.
const LOGS_DIR = process.env.LOGS_DIR;

// NOTA: se pide el TEXTO de la línea, no el número. BugWizard arma el
// contexto vía RAG (indexa+recupera código/logs), lo que no garantiza
// numeración verbatim del archivo original — pedirle el número directamente
// penaliza un error de "conteo" que no refleja si encontró el bug o no. Con
// el texto exacto, condefects-eval/adapter.py lo resuelve contra el archivo
// fuente real (ver resolve_line_numbers), separando "encontró el bug" de
// "supo contar líneas". Debe ser el MISMO prompt para todos los sistemas
// comparados (ver condefects-eval/run_cli_baseline.py).
const DEFAULT_PROMPT = [
  'Analiza el código fuente adjunto e identifica la línea que contiene el bug.',
  'Es un programa corto de programación competitiva.',
  'Termina tu respuesta OBLIGATORIAMENTE con un bloque en este formato exacto:',
  '',
  'ARCHIVO: <nombre_del_archivo>',
  'LINEAS_FALLA_TEXTO:',
  '1. "<texto EXACTO de la línea más probable, tal como aparece en el archivo>"',
  '2. "<texto EXACTO de la segunda línea más probable>"',
  '3. "<texto EXACTO de la tercera línea más probable>"',
  '',
  'No indiques el número de línea: copia el TEXTO EXACTO de cada línea (mismo',
  'contenido y espacios/indentación, sin agregar comentarios ni parafrasear).',
  'Ordena de MÁS a MENOS probable.',
].join('\n');

const PROMPT = process.env.LLM_USER_PROMPT ?? DEFAULT_PROMPT;
// Contenido del archivo de "log". Por defecto "sin logs" (modo source-only puro).
const LOG_TEXT = process.env.LOG_TEXT ?? 'sin logs';

function required(name: string, value: any) {
  if (!value) {
    console.error(`❌ Falta variable de entorno: ${name}`);
    process.exit(1);
  }
}

async function main() {
  required('BACKEND_URL', BACKEND_URL);
  required('BACKEND_WS_URL', BACKEND_WS_URL);
  required('BACKEND_TOKEN', TOKEN);
  required('CHECKOUT_DIR', CHECKOUT_DIR);

  const rows = readManifest(MANIFEST);
  console.log(`📕 Manifiesto: ${rows.length} programas | límite: ${LIMIT}`);

  // Proyectos NIVEL3 ya existentes (por si una corrida previa quedó a medio
  // camino: no reintentar crearlos, reutilizar el id existente).
  let existingProjects = new Map<string, string>();
  try {
    existingProjects = await fetchExistingProjectsByName(BACKEND_URL, TOKEN);
    console.log(`📂 Proyectos existentes detectados: ${existingProjects.size}`);
  } catch (err: any) {
    console.warn(`⚠️  No se pudo listar proyectos existentes (${err?.message ?? err}); se intentará crear todos.`);
  }

  const projects = new ProjectsSocketClient({ backendUrl: BACKEND_WS_URL, token: TOKEN });
  const conversations = new ConversationsSocketClient({ backendUrl: BACKEND_WS_URL, token: TOKEN });
  const messages = new MessagesSocketClient({ backendUrl: BACKEND_WS_URL, token: TOKEN });

  await projects.connect();
  await conversations.connect();
  await messages.connect();

  let done = 0;
  let ok = 0;
  for (const row of rows) {
    if (done >= LIMIT) break;
    done++;

    if (predictionExists(PREDICTIONS_DIR, row.program_key)) {
      console.log(`⏭️  ${row.program_key} (ya tiene predicción, se salta)`);
      ok++;
      continue;
    }

    const faultyPath = path.join(CHECKOUT_DIR, row.rel_path, row.source_file);
    if (!fs.existsSync(faultyPath)) {
      console.error(`❌ ${row.program_key}: no existe ${faultyPath}`);
      continue;
    }

    const stamp = `${row.program_key}@${Date.now()}`;
    console.log(`\n🧩 ${row.program_key}`);

    // Log por-programa si existe (modo con síntoma real), si no, LOG_TEXT global.
    let logText = LOG_TEXT;
    if (LOGS_DIR) {
      const perProgramLogPath = path.join(LOGS_DIR, `${row.program_key}.log`);
      if (fs.existsSync(perProgramLogPath)) {
        logText = fs.readFileSync(perProgramLogPath, 'utf-8');
      } else {
        console.log(`   ⚠️  no hay log en ${perProgramLogPath}, se usa LOG_TEXT`);
      }
    }

    try {
      // 1) proyecto source-only (zip con SOLO el archivo fallado)
      //    Si ya existe un proyecto con este nombre (de una corrida previa que
      //    falló después de crear el proyecto), se reutiliza en vez de
      //    reintentar crearlo (el backend rechaza nombres duplicados por usuario).
      let projectId = existingProjects.get(row.program_key);
      if (projectId) {
        console.log(`   ♻️  proyecto existente reutilizado ${projectId}`);
      } else {
        const zipB64 = buildRepositoryZipBase64(faultyPath, row.source_file);
        const project = await projects.createSourceOnlyProject({
          stamp,
          projectName: row.program_key,
          repositoryZipBase64: zipB64,
        });
        projectId = project.id;
        existingProjects.set(row.program_key, projectId);
        console.log(`   ✅ proyecto ${projectId}`);
      }

      // 2) conversación con archivo de log
      const conversationId = await conversations.createConversationWithLogFile({
        stamp,
        projectId,
        title: row.program_key,
        description: PROMPT,
        logFilename: LOGS_DIR ? `${row.program_key}.log` : 'sin_logs.txt',
        logText,
        allowEmptyLogIndex: true,
      });
      console.log(`   ✅ conversación ${conversationId}`);

      // 3) análisis
      const analysis = await messages.requestAnalysis({ conversationId, description: PROMPT });
      savePrediction(PREDICTIONS_DIR, row.program_key, analysis);
      console.log(`   💾 predicción guardada (${analysis.length} chars)`);
      ok++;
    } catch (err: any) {
      console.error(`   ❌ ${row.program_key}: ${err?.message ?? err}`);
    }
  }

  projects.close();
  conversations.disconnect();
  messages.disconnect();

  console.log(`\n🏁 Terminado. ${ok}/${done} programas con predicción. Carpeta: ${PREDICTIONS_DIR}`);
  process.exit(0);
}

main().catch(err => {
  console.error('Runner failed:', err);
  process.exit(1);
});
