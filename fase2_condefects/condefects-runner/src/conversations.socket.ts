import { io, Socket } from 'socket.io-client';
import { md5OfBase64, parseJwt } from './util';

export class ConversationsSocketClient {
  private socket!: Socket;
  constructor(private readonly opts: { backendUrl: string; token: string }) {}

  connect() {
    this.socket = io(`${this.opts.backendUrl}/conversations`, { path: '/socket.io', transports: ['websocket'] });
    return new Promise<void>((resolve, reject) => {
      this.socket.on('connect', () => resolve());
      this.socket.on('connect_error', reject);
    });
  }

  /**
   * Crea una conversación subiendo un archivo de log (el truco "sin logs").
   * logText es el contenido del archivo (p. ej. "sin logs" o los casos de prueba
   * que fallan, si se usa el modo con síntoma).
   *
   * IMPORTANTE: `joinCreateConversation` y `sendLogFileChunk` son handlers
   * async en el gateway (conversation.gateway.ts) que devuelven un valor —
   * eso es un ack de socket.io. Hay que esperar ese ack antes de continuar,
   * porque el gateway guarda el estado en un Map (`activeClients`) keyed por
   * `client.id + stamp`, y si `createConversation` llega antes de que el join
   * (o el chunk) haya terminado de procesarse, el server responde con errores
   * tipo "No se encontró cliente para adjuntar archivo Log" / "No se hallaron
   * partes de archivos de Log preexistentes" / "Archivo ... no está
   * precargado". Sin esperar los acks, esto es una carrera: puede funcionar
   * por azar en la primera conversación y fallar en las siguientes.
   * `ProjectsSocketClient` ya hace esto bien (ver `emitAndWait`); aquí se
   * replica el mismo patrón.
   */
  async createConversationWithLogFile(params: {
    stamp: string;
    projectId: string;
    title: string;
    description: string;
    logFilename: string;
    logText: string;
    allowEmptyLogIndex: boolean;
  }): Promise<string> {
    const { stamp, projectId, title, description, logFilename, logText, allowEmptyLogIndex } = params;
    const token = this.opts.token;
    const logBase64 = Buffer.from(logText, 'utf-8').toString('base64');
    const checksum = md5OfBase64(logBase64);

    await this.emitAndWait('joinCreateConversation', { stamp, token });

    // subir el archivo de log por chunk (un solo chunk; esperar el ack antes de crear la conversación)
    await this.emitAndWait('sendLogFileChunk', {
      stamp,
      token,
      file: {
        filename: logFilename,
        mimetype: 'text/plain',
        data: logBase64,
        size: Buffer.from(logBase64, 'base64').length,
        checksum,
        partNumber: 1,
        totalParts: 1,
      },
    });

    this.socket.emit('createConversation', {
      stamp,
      token,
      data: {
        projectId,
        title,
        description,
        files: [
          {
            filename: logFilename,
            mimetype: 'text/plain',
            size: Buffer.from(logBase64, 'base64').length,
            checksum,
            partNumber: 1,
            totalParts: 1,
          },
        ],
        imageFiles: [],
        access: 'PRIVATE',
        allowEmptyLogIndex,
        stamp,
        user: parseJwt(token),
      },
    });

    const conversation = await this.waitForEnd('creatingConversation');
    this.socket.emit('leaveCreateConversation', { stamp, token });
    const id = conversation?.id;
    if (!id) throw new Error('No se obtuvo conversationId');
    return id;
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
          reject(new Error(msg?.data?.message ?? 'Error creando conversación'));
        } else {
          console.log('   🟡', msg?.data?.message ?? '');
        }
      };
      this.socket.on(channel, handler);
    });
  }

  disconnect() {
    this.socket.disconnect();
  }
}
