import { loadCatalog } from './catalog/catalog.loader';
import { BackendClient } from './backend/client';
import { ProjectsApi } from './backend/projects/projects.client';
import { ProjectsSocketClient } from './backend/projects/projects.socket';
import { buildContextFile } from './utils/context-file.util';
import { parseJwt } from './utils/jwt.util';
import { CredentialsClient } from './backend/credentials/credentials.client';
import { buildDateRangeFromHours } from './utils/date.util';
import { createRunId, storeAnalysisResult, storeRawAnalysisMarkdown } from './utils/analysis-storage.util';
import { runAnalysis } from './backend/analysis';
import { mapCredentials } from './utils/credential-mapper.util';

async function main() {
  const args = process.argv.slice(2);
  const isPrepareMode = args.includes('--prepare');
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
  // 02 - RECUPERA CREDENCIALES
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
  // 03 - DETERMINA LAS FALTANTES
  // ================================================

  const backendCredentialNames = new Set(
    backendCredentials.map(c => c.title),
  );

  const missingCredentials = catalog.credentials.filter(
    c => !backendCredentialNames.has(c.name),
  );

  const existingCredentials = catalog.credentials.filter(
    c => backendCredentialNames.has(c.name),
  );

  if (missingCredentials.length > 0) {
    console.log('Catalog credentials missing in backend:');
    missingCredentials.forEach(c => console.log(`- ❌ 🔑 ${c.name} [${c.type}]`));
  }

  // ================================================
  // 04 - CREA CREDENCIALES
  // ================================================

  const credentialsToCreate = missingCredentials.map(c => mapCredentials(c));

  for (const dto of credentialsToCreate) {
    console.log(`🔐 Creating credential: ${dto.title} (${dto.type})`);

    const created = await credentialsClient.create(dto);
    backendCredentials.push(created);

    console.log(`✅ Created: ${created.title} → ${created.id}`);
  }

  // ================================================
  // 05 - FUERZA ACTUALIZACIONES
  // ================================================

  for (const credential of existingCredentials) {
    if (credential.forceUpdate) {
      const backendCredential = backendCredentials.find(c => c.title === credential.name);

      if (!backendCredential) {
        throw new Error(`Credential not found: ${credential.name}`);
      }

      console.log(`🔐 💪 Forzando actualización de credenciales: ${credential.name} (${credential.type})`);
      
      await credentialsClient.update(backendCredential.id, mapCredentials(credential));

      console.log(`🔐 ✅ Credenciales actualizadas: ${credential.name} (${credential.type})`);
    }
  }

  // ================================================
  // 06 - RECUPERA PROYECTOS
  // ================================================

  const projectsApi = new ProjectsApi(backend);

  console.log('🔄 Fetching projects from backend...');
  let projects = await projectsApi.list();

  projects = projects.filter(p => !p.global); 

  console.log('Projects in backend:');
  for (const p of projects) {
    const isOnCatalog = catalog.projects.some(cp => cp.name === p.projectName) ? '📕 ' : '';
    console.log(`- 🏗️  ${isOnCatalog}${p.projectName} (${p.id})`);
  }

  // ================================================
  // 07 - DETERMINA LOS FALTANTES
  // ================================================

  const normalize = (s: string) => s.trim().toLowerCase();

  const backendNames = new Set(
    projects.map(p => normalize(p.projectName))
  );

  const missingProjects = catalog.projects.filter(
    p => !backendNames.has(normalize(p.name))
  );

  const existingProjects = catalog.projects.filter(
    p => backendNames.has(normalize(p.name))
  );

  if (missingProjects.length > 0) {
    console.log('Catalog projects missing in backend:');
    missingProjects.forEach(p => console.log(`- ❌ 🏗️  ${p.name}`));
  }

  // ================================================
  // 08 - CREA LOS PROYECTOS FALTANTES
  // ================================================

  const socketClient = new ProjectsSocketClient({
    backendUrl: process.env.BACKEND_WS_URL!,
    token: process.env.BACKEND_TOKEN!,
  });

  await socketClient.connect();

  for (const project of missingProjects) {
    console.log(`🚀 Creando proyecto: ${project.name}`);

    const stamp = `${project.name}@${Date.now()}`;
    const contextFile = buildContextFile(project.context);

    const cloudwatchCredential = backendCredentials.find(
      c => c.title === project.logs.credentials && c.type === 'CLOUDWATCH'
    );

    if (!cloudwatchCredential) {
      throw new Error(`CloudWatch credential not found for project: ${project.name}`);
    }

    const repositoryCredential = backendCredentials.find(
      c => c.title === project.sources.credentials && ['GITHUB_PAT', 'BITBUCKET_API_TOKEN'].includes(c.type)
    );

    if (!repositoryCredential) {
      throw new Error(`Repository credential not found for project: ${project.name}`);
    }

    const result = await socketClient.createProject({
      stamp,
      contextFile: contextFile.withData,
      projectData: {
        projectName: project.name,
        repositoryType: 'repositorio',
        repositoryPaths: project.sources.repository,
        logType: ['cloudwatch'],
        logPaths: project.logs.logGroups.join(','),
        query: '',
        contextFile: contextFile.withoutData,
        cloudwatchAccount: cloudwatchCredential.id,
        repositoryAccount: repositoryCredential.id,
        global: false,
        monitor: false,
        securityIssue: false,
        stamp,
        user: parseJwt(process.env.BACKEND_TOKEN!),
      },
    });

    projects.push({
      id: result.id,
      projectName: project.name,
      global: false
    });

    console.log(`✅ Proyecto creado: ${project.name} (${result.id})`);
  }

  socketClient.close();

  // ================================================
  // 09 - ACTUALIZA LOS QUE YA EXISTEN
  // ================================================

  console.log(`🗃️  Verificando estado de repositorios...`);

  for (const project of existingProjects) {
    const backendProject = projects.find(p => p.projectName === project.name);

    if (!backendProject) {
      throw new Error(`Project not found for project: ${project.name}`);
    }

    const projectBehindRemote = await projectsApi.getBehindRemote(backendProject.id);

    if (projectBehindRemote.isBehindRemote) {
      console.log(`- ❌ Repositorios desactualizados: ${project.name} (${backendProject.id})`);

      const reposToUpdate = projectBehindRemote.repositories.filter(r => r.isOutdated).map(r => r.repoSlug);

      await projectsApi.updateRepositories(backendProject.id, reposToUpdate);

      console.log(`- ✅ Repositorios actualizados: ${project.name} (${backendProject.id})`);
    } else {
      console.log(`- 🗃️  Repositorios al día: ${project.name} (${backendProject.id})`);
    }
  }

  if (isPrepareMode) {
    console.log('🟡 Modo prepare activo: se omite análisis.');
    process.exit(0);
  }

  // ================================================
  // 10 - CORRE LOS ANALISIS
  // ================================================

  const defaultRange = buildDateRangeFromHours(24 * 6);

  for (const project of catalog.projects) {
    if (!project.analyze) continue;

    const range = project.logs.range ?? defaultRange;

    console.log(`🧠 Iniciando análisis para proyecto: ${project.name} (${range.startTime} a ${range.endTime})`);

    const backendProject = projects.find(p => p.projectName === project.name);

    if (!backendProject) {
      throw new Error(`Project not found for project: ${project.name}`);
    }

    const prompt = project.prompts && project.prompts.length > 0 ? project.prompts[0] : process.env.LLM_USER_PROMPT!;

    try {
      const { conversationId, analysis } = await runAnalysis({
        backendUrl: process.env.BACKEND_URL!,
        token: process.env.BACKEND_TOKEN!,
        payload: {
          stamp: `${project.name}@${Date.now()}`,
          data: {
            title: project.name,
            description: prompt,
            projectId: backendProject.id,
            files: [],
            imageFiles: [],
            startTime: range.startTime,
            endTime: range.endTime,
            access: 'PRIVATE',
            user: parseJwt(process.env.BACKEND_TOKEN!),
          },
        },
      });

      await storeAnalysisResult({
        project: project.name,
        conversationId,
        backendUrl: process.env.BACKEND_WS_URL!,
        timeRange: range,
        analysis: analysis.replace('[[START_OF_MESSAGE]]', ''),
      });

      const runId = createRunId();
      await storeRawAnalysisMarkdown({
        project: project.name,
        analysis: analysis.replace('[[START_OF_MESSAGE]]', ''),
        runId,
      });

      console.log(`✅ Análisis finalizado: ${project.name}`);
      console.log(`🆔 Conversation ID: ${conversationId}`);
    } catch (err) {
      console.error(`❌ Error en análisis del proyecto ${project.name}`, err);
    }
  }

  console.log('🏁 Análisis de catálogo finalizado');
}

main().catch(err => {
  console.error('Runner failed:', err);
  process.exit(1);
});
