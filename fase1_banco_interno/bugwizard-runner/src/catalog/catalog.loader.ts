import fs from 'node:fs';
import { CatalogSchema, Catalog } from './catalog.schema';

export function loadCatalog(path: string): Catalog {
  const raw = fs.readFileSync(path, 'utf-8');
  const json = JSON.parse(raw);
  return CatalogSchema.parse(json);
}
