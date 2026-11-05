import { io, Socket } from 'socket.io-client';

interface ConversationsSocketOptions {
  backendUrl: string;
  token: string;
}

export class ConversationsSocketClient {
  private socket!: Socket;

  constructor(private readonly opts: ConversationsSocketOptions) {}

  connect() {
    this.socket = io(`${this.opts.backendUrl}/conversations`, {
      path: '/socket.io',
      transports: ['websocket'],
    });

    return new Promise<void>((resolve, reject) => {
      this.socket.on('connect', () => resolve());
      this.socket.on('connect_error', reject);
    });
  }

  createConversation(payload: {
    stamp: string;
    data: any;
  }): Promise<string> {
    return new Promise((resolve, reject) => {
      const token = this.opts.token;

      this.socket.emit('joinCreateConversation', {
        stamp: payload.stamp,
        token,
      });

      this.socket.emit('createConversation', {
        stamp: payload.stamp,
        token,
        data: payload.data,
      });

      const handler = (msg: any) => {
        if (msg?.content === '[[END_OF_MESSAGE]]') {
          const conversationId = msg?.data?.obj?.id;

          this.socket.off('creatingConversation', handler);
          this.socket.emit('leaveCreateConversation', {
            stamp: payload.stamp,
            token,
          });

          if (!conversationId) {
            reject(new Error('Conversation ID not found'));
            return;
          }

          resolve(conversationId);
        }

        if (msg?.content === '[[ERROR_MESSAGE]]') {
          this.socket.off('creatingConversation', handler);
          reject(new Error(msg?.data?.message ?? 'Error creating conversation'));
        }
      };

      this.socket.on('creatingConversation', handler);
    });
  }

  disconnect() {
    this.socket.disconnect();
  }
}
