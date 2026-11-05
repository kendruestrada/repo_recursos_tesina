import { ConversationsSocketClient } from "./conversations/conversations.socket";
import { MessagesSocketClient } from "./messages/messages.socket";

interface RunAnalysisOptions {
  backendUrl: string;
  token: string;
  payload: {
    stamp: string;
    data: {
      title: string;
      description: string;
      projectId: string;
      files: unknown[];
      imageFiles: unknown[];
      startTime: string;
      endTime: string;
      access: 'PRIVATE' | 'PUBLIC';
      user: any;
    };
  };
}

export async function runAnalysis(
  opts: RunAnalysisOptions
): Promise<{ conversationId: string; analysis: string }> {
  const conversations = new ConversationsSocketClient({
    backendUrl: opts.backendUrl,
    token: opts.token,
  });

  const messages = new MessagesSocketClient({
    backendUrl: opts.backendUrl,
    token: opts.token,
  });

  try {
    await conversations.connect();
    await messages.connect();

    const conversationId = await conversations.createConversation({
      stamp: opts.payload.stamp,
      data: opts.payload.data,
    });

    const analysis = await messages.requestAnalysis({
      conversationId,
      description: opts.payload.data.description,
      startTime: opts.payload.data.startTime,
      endTime: opts.payload.data.endTime,
      user: opts.payload.data.user,
    });

    return { conversationId, analysis };
  } finally {
    conversations.disconnect();
    messages.disconnect();
  }
}
