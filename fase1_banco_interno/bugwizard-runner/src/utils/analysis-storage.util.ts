import { promises as fs } from 'fs';
import * as path from 'path';

interface TimeRange {
  startTime: string;
  endTime: string;
}

interface StoreAnalysisOptions {
  project: string;
  conversationId?: string;
  backendUrl: string;
  timeRange: TimeRange;
  analysis: unknown;
}

const BASE_DIR = path.resolve(process.cwd(), 'analysis-history');

export async function storeAnalysisResult(
  opts: StoreAnalysisOptions,
): Promise<void> {
  const executedAt = new Date().toISOString();

  const projectDir = path.join(BASE_DIR, sanitize(opts.project));
  await fs.mkdir(projectDir, { recursive: true });

  const fileName = `${sanitizeTimestamp(executedAt)}.json`;
  const filePath = path.join(projectDir, fileName);

  const payload = {
    version: 1,
    project: opts.project,
    conversationId: opts.conversationId,
    executedAt,
    timeRange: opts.timeRange,
    backendUrl: opts.backendUrl,
    analysis: opts.analysis,
  };

  await fs.writeFile(filePath, JSON.stringify(payload, null, 2), 'utf-8');

  // opcional: latest.json como puntero rápido
  const latestPath = path.join(projectDir, 'latest.json');
  await fs.writeFile(latestPath, JSON.stringify(payload, null, 2), 'utf-8');
}

/**
 * Evita caracteres raros en nombres de carpeta
 */
function sanitize(value: string): string {
  return value.replace(/[^a-zA-Z0-9-_]/g, '_');
}

/**
 * Evita ":" que rompe en Windows
 */
function sanitizeTimestamp(iso: string): string {
  return iso.replace(/[:]/g, '-');
}

// ALMACENAMIENTO EN ESTRUCTURA ALTERNATIVA (analysis/run-timestamp/proyecto.md)

interface StoreRawAnalysisOptions {
  project: string;
  analysis: string; // acá asumimos markdown crudo
  runId: string;
}

const RAW_BASE_DIR = path.resolve(process.cwd(), 'analysis');

export async function storeRawAnalysisMarkdown(
  opts: StoreRawAnalysisOptions,
): Promise<void> {
  const runDir = path.join(RAW_BASE_DIR, opts.runId);

  await fs.mkdir(runDir, { recursive: true });

  const fileName = `${sanitize(opts.project)}.md`;
  const filePath = path.join(runDir, fileName);

  await fs.writeFile(filePath, opts.analysis, 'utf-8');
}

export function createRunId(date = new Date()): string {
  const pad = (n: number) => n.toString().padStart(2, '0');

  return `run-${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate(),
  )}-${pad(date.getHours())}-${pad(date.getMinutes())}-${pad(
    date.getSeconds(),
  )}`;
}
