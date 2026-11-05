import { BackendClient } from '../client';
import { BackendProject, BackendProjectBehindRemote } from './projects.schema';

export class ProjectsApi {
  constructor(private readonly client: BackendClient) {}

  async list(): Promise<BackendProject[]> {
    return this.client.get<BackendProject[]>(
      '/projects?projectType=NIVEL3'
    );
  }

  async getBehindRemote(
    projectId: string
  ): Promise<BackendProjectBehindRemote> {
    return this.client.get<BackendProjectBehindRemote>(
      `/projects/${projectId}/extras/BEHIND_REMOTE`
    );
  }

  async updateRepositories(
    projectId: string,
    repositories: string[]
  ): Promise<void> {
    await this.client.put(
      `/projects/${projectId}/repositories`,
      { repositories }
    );
  }

  async delete(projectId: string): Promise<void> {
    await this.client.delete(
      `/projects/${projectId}/false`
    );
  }
}