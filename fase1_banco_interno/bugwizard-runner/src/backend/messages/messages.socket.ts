import { io, Socket } from 'socket.io-client';

interface MessagesSocketOptions {
  backendUrl: string;
  token: string;
}

export class MessagesSocketClient {
  private socket!: Socket;

  constructor(private readonly opts: MessagesSocketOptions) {}

  connect() {
    this.socket = io(`${this.opts.backendUrl}/messages`, {
      path: '/socket.io',
      transports: ['websocket'],
    });

    return new Promise<void>((resolve, reject) => {
      this.socket.on('connect', () => resolve());
      this.socket.on('connect_error', reject);
    });
  }

  requestAnalysis(payload: {
    conversationId: string;
    description: string;
    startTime: string;
    endTime: string;
    user: any;
  }): Promise<string> {
    return new Promise(resolve => {
      const token = this.opts.token;
      let buffer = '';

      this.socket.emit('joinConversation', {
        conversationId: payload.conversationId,
        token,
      });

      const handler = (msg: any) => {
        if (msg?.messageType !== 'ai') return;

        if (msg.content === '[[END_OF_MESSAGE]]') {
          this.socket.off('responseMessage', handler);
          resolve(buffer.trim());
          return;
        }

        buffer += msg.content ?? '';
      };

      this.socket.on('responseMessage', handler);

      this.socket.emit('requestMessage', {
        conversationId: payload.conversationId,
        content: payload.description,
        dateRange: {
          from: payload.startTime,
          to: payload.endTime,
        },
        userId: payload.user.username,
        token: `Bearer ${token}`,
      });
    });
  }

  disconnect() {
    this.socket.disconnect();
  }
}
