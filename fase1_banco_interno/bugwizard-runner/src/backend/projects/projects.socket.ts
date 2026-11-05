import { io, Socket } from 'socket.io-client';

interface CreateProjectOptions {
  backendUrl: string;
  token: string;
}

export class ProjectsSocketClient {
  private socket!: Socket;

  constructor(private readonly opts: CreateProjectOptions) {}

  connect() {
    this.socket = io(`${this.opts.backendUrl}/projects`, {
    path: '/socket.io',
    transports: ['websocket'],
    });

    return new Promise<void>((resolve, reject) => {
      this.socket.on('connect', () => resolve());
      this.socket.on('connect_error', reject);
    });
  }

  async createProject(params: {
    stamp: string;
    contextFile: {
      filename: string;
      mimetype: string;
      data: string;
      size: number;
      checksum: string;
      totalParts: number;
      partNumber: number;
    };
    projectData: {
      repositoryType: string;
      projectName: string;
      logType: string[];
      logPaths: string;
      query: string;
      repositoryPaths: string;
      contextFile: {
          filename: string;
          mimetype: string;
          size: number;
          checksum: string;
          totalParts: number;
          partNumber: number;
      };
      cloudwatchAccount: string;
      repositoryAccount: string;
      monitor: boolean;
      global: boolean;
      securityIssue: boolean;
      stamp: string;
      user: any;
    };
  }) {
    const { stamp, contextFile, projectData } = params;

    // 1️⃣ join
    await this.emitAndWait('joinCreateProject', {
      stamp,
      token: this.opts.token,
    });

    // 2️⃣ upload context
    await this.emitAndWait('sendProjectFileChunk', {
      stamp,
      file: contextFile,
      token: this.opts.token,
    });

    // 3️⃣ create project
    this.socket.emit('createProject', {
      data: projectData,
      token: this.opts.token,
    });

    // 4️⃣ wait for END_OF_MESSAGE
    const result = await this.waitForEndMessage();

    // 5️⃣ leave
    this.socket.emit('leaveCreateProject', {
      stamp,
      token: this.opts.token,
    });

    return result;
  }

  private emitAndWait(event: string, payload: any): Promise<any> {
    return new Promise((resolve, reject) => {
      this.socket.emit(event, payload, (ack: any) => {
        if (ack?.error) return reject(ack.error);
        resolve(ack);
      });
    });
  }

  private waitForEndMessage(): Promise<any> {
    return new Promise(resolve => {
      const handler = (msg: { content: any; data: any; }) => {
        const { content, data } = msg;

        if (content === '[[END_OF_MESSAGE]]') {
          this.socket.off('creatingProject', handler);
          resolve(data?.obj);
        } else {
          console.log('🟡', data?.message ?? data);
        }
      };
      this.socket.on('creatingProject', handler);
    });
  }

  close() {
    this.socket.disconnect();
  }
}