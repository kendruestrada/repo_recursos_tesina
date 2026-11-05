import { z } from 'zod';

export const CredentialTypeSchema = z.enum([
  'GITHUB_PAT',
  'BITBUCKET_API_TOKEN',
  'CLOUDWATCH',
]);

export const CredentialSchema = z.object({
  id: z.string().uuid(),
  userId: z.string(),
  title: z.string().min(1),
  type: CredentialTypeSchema,
  typeCreatedAt: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
  global: z.number().optional(),
});

export type BackendCredential = z.infer<typeof CredentialSchema>;

// =======================
// Schemas de creación
// =======================

const BaseCreateCredentialSchema = z.object({
  title: z.string().min(1),
  global: z.boolean().optional().default(false),
});

export const CreateGithubPatCredentialSchema =
  BaseCreateCredentialSchema.extend({
    type: z.literal('GITHUB_PAT'),
    credentials: z.object({
      accessToken: z.string().min(1),
    }),
  });

export const CreateBitbucketApiTokenCredentialSchema =
  BaseCreateCredentialSchema.extend({
    type: z.literal('BITBUCKET_API_TOKEN'),
    credentials: z.object({
      apiToken: z.string().min(1),
      username: z.string().min(1),
    }),
  });

export const CreateCloudwatchCredentialSchema =
  BaseCreateCredentialSchema.extend({
    type: z.literal('CLOUDWATCH'),
    credentials: z.object({
      accessKeyId: z.string().min(1),
      secretAccessKey: z.string().min(1),
      sessionToken: z.string().min(1).optional(),
      region: z.string().min(1),
    }),
  });

export const CreateCredentialSchema = z.discriminatedUnion('type', [
  CreateGithubPatCredentialSchema,
  CreateBitbucketApiTokenCredentialSchema,
  CreateCloudwatchCredentialSchema,
]);

export type CreateCredentialDto = z.infer<typeof CreateCredentialSchema>;
