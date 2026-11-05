import { BackendClient } from "./backend/client";
import { CredentialsClient } from "./backend/credentials/credentials.client";
import { ProjectsApi } from "./backend/projects/projects.client";
import { loadCatalog } from "./catalog/catalog.loader";

async function main() {
  const args = process.argv.slice(2);
  const positionalArgs = args.filter(arg => !arg.startsWith('--'));
  const catalogPath = positionalArgs[0] ?? 'catalog.json';

  const backend = new BackendClient(
    process.env.BACKEND_URL!,
    process.env.BACKEND_TOKEN!,
  );

  // ================================================
  // 01 - CARGA CATALOGO
  // ================================================

  console.log('Loading catalog:', catalogPath);
  const catalog = loadCatalog(catalogPath);

  console.log(`📕 Catalog loaded: ${catalog.projects.length} projects, ${catalog.credentials.length} credentials`);
  
  // ================================================
  // 02 - RECUPERA PROYECTOS
  // ================================================

  const projectsApi = new ProjectsApi(backend);

  console.log('🔄 Fetching projects from backend...');
  let backendProjects = await projectsApi.list();

  backendProjects = backendProjects.filter(p => !p.global); 

  console.log('Projects in backend:');
  for (const p of backendProjects) {
    const isOnCatalog = catalog.projects.some(cp => cp.name === p.projectName) ? '📕 ' : '';
    console.log(`- 🏗️  ${isOnCatalog}${p.projectName} (${p.id})`);
  }

  // ================================================
  // 03 - DETERMINA LOS CREADOS
  // ================================================

  const normalize = (s: string) => s.trim().toLowerCase();

  const backendNames = new Set(
    backendProjects.map(p => normalize(p.projectName))
  );

  const existingProjects = catalog.projects.filter(
    p => backendNames.has(normalize(p.name))
  );

  // ================================================
  // 04 - ELIMINA LOS EXISTENTES
  // ================================================

  console.log('Eliminando proyectos:');
  for (const project of existingProjects) {
    const backendProject = backendProjects.find(p => p.projectName === project.name);

    if (!backendProject) {
        throw new Error(`Project not found: ${project.name}`);
    }

    await projectsApi.delete(backendProject.id);
    console.log(`💥 Proyecto eliminado: ${project.name} (${backendProject.id})`);
  }

  // ================================================
  // 05 - RECUPERA CREDENCIALES
  // ================================================

  const credentialsClient = new CredentialsClient(backend);

  console.log('🔄 Fetching credentials from backend...');
  const backendCredentials = await credentialsClient.list();

  console.log('Credentials in backend:');
  for (const c of backendCredentials) {
    const isOnCatalog = catalog.credentials.some(cc => cc.name === c.title) ? '📕 ' : '';
    console.log(`- 🔑 ${isOnCatalog}${c.title} (${c.id})`);
  }

  // ================================================
  // 06 - DETERMINA LAS CREADAS
  // ================================================

  const backendCredentialNames = new Set(
    backendCredentials.map(c => c.title),
  );

  const existingCredentials = catalog.credentials.filter(
    c => backendCredentialNames.has(c.name),
  );

  // ================================================
  // 07 - ELIMINA LAS EXISTENTES
  // ================================================

  console.log('Eliminando credenciales:');
  for (const credential of existingCredentials) {
    const backendCredential = backendCredentials.find(c => c.title === credential.name);

    if (!backendCredential) {
        throw new Error(`Credential not found: ${credential.name}`);
    }

    await credentialsClient.delete(backendCredential.id);
    console.log(`💥 Credencial eliminada: ${credential.name} (${backendCredential.id})`);
  }

  console.log('🏁 Eliminación de catálogo finalizada');
}

main().catch(err => {
  console.error('Runner failed:', err);
  process.exit(1);
});
