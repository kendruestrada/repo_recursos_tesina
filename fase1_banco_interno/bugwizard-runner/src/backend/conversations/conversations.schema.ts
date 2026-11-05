type CreateConversationPayload = {
  stamp: string;
  token: string;
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

type AnalysisResult = {
  conversationId: string;
  analysis: string;
};
