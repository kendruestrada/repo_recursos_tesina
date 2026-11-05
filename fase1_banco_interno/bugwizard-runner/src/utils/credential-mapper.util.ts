import { Credential } from "../catalog/catalog.schema";

export const mapCredentials = (c: Credential) => {
  switch (c.type) {
    case 'github_pat':
      return {
        title: c.name,
        type: 'GITHUB_PAT' as const,
        global: false,
        credentials: {
          accessToken: c.token,
        },
      };

    case 'bitbucket_api_token':
      return {
        title: c.name,
        type: 'BITBUCKET_API_TOKEN' as const,
        global: false,
        credentials: {
          apiToken: c.token,
          username: c.username,
        },
      };

    case 'cloudwatch':
      return {
        title: c.name,
        type: 'CLOUDWATCH' as const,
        global: false,
        credentials: {
          accessKeyId: c.accessKeyId,
          secretAccessKey: c.secretAccessKey,
          sessionToken: c.sessionToken,
          region: c.region ?? 'us-east-1',
        },
      };

    default:
      // protección futura si el catálogo crece
      throw new Error(`Unsupported credential type: ${(c as any).type}`);
  }
}