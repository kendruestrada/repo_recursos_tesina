import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import AdmZip from 'adm-zip';

/** md5 hex del STRING base64 (así lo valida el backend: calculateBase64Hash). */
export function md5OfBase64(base64: string): string {
  return crypto.createHash('md5').update(base64).digest('hex');
}

/** Decodifica el payload de un JWT (igual que el front de BugWizard). */
export function parseJwt(token: string): any {
  const part = token.split('.')[1];
  if (!part) return null;
  const b64 = part.replace(/-/g, '+').replace(/_/g, '/');
  const json = Buffer.from(b64, 'base64').toString('utf-8');
  return JSON.parse(json);
}

/**
 * Construye un repository.zip (en base64) que contiene SOLO el archivo fallado.
 * IMPORTANTE: NO incluir correctVersion.* ni faultLocation.txt — eso filtraría
 * la respuesta al agente e invalidaría la evaluación.
 */
export function buildRepositoryZipBase64(faultySourcePath: string, entryName: string): string {
  const zip = new AdmZip();
  zip.addLocalFile(faultySourcePath, '', entryName);
  return zip.toBuffer().toString('base64');
}

export interface ManifestRow {
  program_key: string;
  task: string;
  language: string;
  program_id: string;
  source_file: string;
  gold_lines: string;
  rel_path: string;
}

/** Parser CSV mínimo (los campos del manifiesto no llevan comas ni comillas). */
export function readManifest(manifestPath: string): ManifestRow[] {
  const text = fs.readFileSync(manifestPath, 'utf-8').trim();
  const lines = text.split(/\r?\n/);
  const header = lines[0].split(',');
  const rows: ManifestRow[] = [];
  for (const line of lines.slice(1)) {
    if (!line.trim()) continue;
    const cols = line.split(',');
    const row: any = {};
    header.forEach((h, i) => (row[h] = cols[i]));
    rows.push(row as ManifestRow);
  }
  return rows;
}

export function ensureDir(dir: string) {
  fs.mkdirSync(dir, { recursive: true });
}

export function savePrediction(predictionsDir: string, programKey: string, markdown: string) {
  ensureDir(predictionsDir);
  fs.writeFileSync(path.join(predictionsDir, `${programKey}.md`), markdown, 'utf-8');
}

export function predictionExists(predictionsDir: string, programKey: string): boolean {
  return fs.existsSync(path.join(predictionsDir, `${programKey}.md`));
}

/**
 * Trae los proyectos NIVEL3 ya existentes del usuario (REST: GET /projects)
 * y devuelve un mapa projectName -> projectId.
 *
 * El nombre de proyecto que usa este runner es el `program_key`, y el backend
 * rechaza crear un proyecto con un nombre repetido para el mismo usuario
 * ("Proyecto ya existe con el mismo nombre para el usuario"). Esto pasa si
 * una corrida anterior alcanzó a crear el proyecto pero falló en un paso
 * posterior (p. ej. la conversación) — al reintentar, hay que REUTILIZAR el
 * proyecto existente en vez de intentar crear uno nuevo.
 */
export async function fetchExistingProjectsByName(
  backendUrl: string,
  token: string,
): Promise<Map<string, string>> {
  const url = `${backendUrl.replace(/\/$/, '')}/projects?projectType=NIVEL3`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`GET /projects -> ${res.status} ${res.statusText}`);
  }
  const projects = (await res.json()) as Array<{ id: string; projectName: string }>;
  const map = new Map<string, string>();
  for (const p of projects) {
    if (p.projectName) map.set(p.projectName, p.id);
  }
  return map;
}
