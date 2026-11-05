import { io, Socket } from 'socket.io-client';
import { parseJwt } from './util';

// Tope por análisis: si el backend corta el stream sin mandar
// END_OF_MESSAGE/ERROR_MESSAGE, la promesa quedaría colgada para siempre.
const ANALYSIS_TIMEOUT_MS = Number(process.env.ANALYSIS_TIMEOUT_MS ?? 10 * 60 * 1000);

export class MessagesSocketClient {
  private socket!: Socket;
  constructor(private readonly opts: { backendUrl: string; token: string }) {}

  connect() {
    this.socket = io(`${this.opts.backendUrl}/messages`, { path: '/socket.io', transports: ['websocket'] });
    return new Promise<void>((resolve, reject) => {
      this.socket.on('connect', () => resolve());
      this.socket.on('connect_error', reject);
    });
  }

  /** Pide el análisis y acumula el stream de la IA hasta END_OF_MESSAGE. */
  requestAnalysis(payload: { conversationId: string; description: string }): Promise<string> {
    return new Promise((resolve, reject) => {
      const token = this.opts.token;
      const user = parseJwt(token);
      let buffer = '';
      const timer = setTimeout(() => {
        this.socket.off('responseMessage', handler);
        reject(new Error(`Timeout de análisis (${ANALYSIS_TIMEOUT_MS / 1000}s sin END_OF_MESSAGE)`));
      }, ANALYSIS_TIMEOUT_MS);

      this.socket.emit('joinConversation', { conversationId: payload.conversationId, token });

      const handler = (msg: any) => {
        if (msg?.messageType !== 'ai') return;
        if (msg.content === '[[END_OF_MESSAGE]]') {
          clearTimeout(timer);
          this.socket.off('responseMessage', handler);
          resolve(buffer.replace('[[START_OF_MESSAGE]]', '').trim());
          return;
        }
        if (msg.content === '[[ERROR_MESSAGE]]') {
          clearTimeout(timer);
          this.socket.off('responseMessage', handler);
          reject(new Error('Error en el análisis'));
          return;
        }
        buffer += msg.content ?? '';
      };
      this.socket.on('responseMessage', handler);

      this.socket.emit('requestMessage', {
        conversationId: payload.conversationId,
        content: payload.description,
        userId: user?.username,
        token: `Bearer ${token}`,
      });
    });
  }

  disconnect() {
    this.socket.disconnect();
  }
}
