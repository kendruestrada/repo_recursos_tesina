import { io, Socket } from 'socket.io-client';
import { md5OfBase64, parseJwt } from './util';

const NIL_UUID = '00000000-0000-0000-0000-000000000000';

export class ProjectsSocketClient {
  private socket!: Socket;
  constructor(private readonly opts: { backendUrl: string; token: string }) {}

  connect() {
    this.socket = io(`${this.opts.backendUrl}/projects`, { path: '/socket.io', transports: ['websocket'] });
    return new Promise<void>((resolve, reject) => {
      this.socket.on('connect', () => resolve());
      this.socket.on('connect_error', reject);
    });
  }

  /**
   * Crea un proyecto NIVEL3 source-only:
   *  - repositoryType = zip  (sube repository.zip con el código fallado)
   *  - logType = ['file']    (los logs se suben por conversación, no CloudWatch)
   * No requiere credenciales de git/CloudWatch/NewRelic.
   */
  async createSourceOnlyProject(params: {
    stamp: string;
    projectName: string;
    repositoryZipBase64: string;
  }): Promise<any> {
    const { stamp, projectName, repositoryZipBase64 } = params;
    const token = this.opts.token;
    const checksum = md5OfBase64(repositoryZipBase64);

    await this.emitAndWait('joinCreateProject', { stamp, token });

    // subir repository.zip (un solo chunk; los programas de ConDefects son diminutos)
    await this.emitAndWait('sendProjectFileChunk', {
      stamp,
      token,
      file: {
        filename: 'repository.zip',
        mimetype: 'application/zip',
        data: repositoryZipBase64,
        size: Buffer.from(repositoryZipBase64, 'base64').length,
        checksum,
        partNumber: 1,
        totalParts: 1,
      },
    });

    this.socket.emit('createProject', {
      token,
      data: {
        projectName,
        repositoryType: 'zip',
        repositoryFile: {
          filename: 'repository.zip',
          mimetype: 'application/zip',
          size: Buffer.from(repositoryZipBase64, 'base64').length,
          checksum,
          partNumber: 1,
          totalParts: 1,
        },
        contextFile: null,
        repositoryPaths: '',
        logType: ['file'],
        logPaths: '',
        query: '',
        repositoryAccount: NIL_UUID,
        cloudwatchAccount: NIL_UUID,
        newRelicAccount: NIL_UUID,
        projectType: 'NIVEL3',
        global: false,
        monitor: false,
        securityIssue: false,
        stamp,
        user: parseJwt(token),
      },
    });

    const project = await this.waitForEnd('creatingProject');
    this.socket.emit('leaveCreateProject', { stamp, token });
    return project;
  }

  private emitAndWait(event: string, payload: any): Promise<any> {
    return new Promise((resolve, reject) => {
      this.socket.emit(event, payload, (ack: any) => {
        if (ack?.error) return reject(new Error(ack.error));
        resolve(ack);
      });
    });
  }

  private waitForEnd(channel: string): Promise<any> {
    return new Promise((resolve, reject) => {
      const handler = (msg: any) => {
        if (msg?.content === '[[END_OF_MESSAGE]]') {
          this.socket.off(channel, handler);
          resolve(msg?.data?.obj);
        } else if (msg?.content === '[[ERROR_MESSAGE]]') {
          this.socket.off(channel, handler);
          reject(new Error(msg?.data?.message ?? 'Error creando proyecto'));
        } else {
          console.log('   🟡', msg?.data?.message ?? '');
        }
      };
      this.socket.on(channel, handler);
    });
  }

  close() {
    this.socket.disconnect();
  }
}
