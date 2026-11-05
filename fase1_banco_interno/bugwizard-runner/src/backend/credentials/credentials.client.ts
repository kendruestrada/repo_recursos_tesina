import { BackendClient } from '../client';
import { BackendCredential, CreateCredentialDto, CreateCredentialSchema } from './credentials.schema';

export class CredentialsClient {
  constructor(private readonly client: BackendClient) {}

  async list(): Promise<BackendCredential[]> {
    return this.client.get<BackendCredential[]>(
      '/credentials/user'
    );
  }

  async create(
    payload: CreateCredentialDto
  ): Promise<BackendCredential> {
    const data = CreateCredentialSchema.parse(payload);

    return this.client.post<BackendCredential, CreateCredentialDto>(
      '/credentials',
      data
    );
  }

  async update(
    credentialId: string,
    payload: CreateCredentialDto
  ): Promise<BackendCredential> {
    const data = CreateCredentialSchema.parse(payload);

    return this.client.put<BackendCredential, CreateCredentialDto>(
      `/credentials/${credentialId}`,
      data
    );
  }

  async delete(credentialId: string): Promise<void> {
    await this.client.delete(
      `/credentials/${credentialId}`
    );
  }
}
