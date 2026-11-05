import { z } from 'zod';

/* ============================
 * Credentials
 * ============================ */

const BitbucketCredentialSchema = z.object({
  name: z.string().min(1),
  type: z.literal('bitbucket_api_token'),
  forceUpdate: z.boolean().optional().default(false),
  token: z.string().min(1),
  username: z.string().min(1),
});

const GithubCredentialSchema = z.object({
  name: z.string().min(1),
  type: z.literal('github_pat'),
  forceUpdate: z.boolean().optional().default(false),
  token: z.string().min(1),
});

const CloudWatchCredentialSchema = z.object({
  name: z.string().min(1),
  type: z.literal('cloudwatch'),
  forceUpdate: z.boolean().optional().default(false),
  accessKeyId: z.string().min(1),
  secretAccessKey: z.string().min(1),
  sessionToken: z.string().min(1),
  region: z.string().min(1).optional(),
});

/**
 * Unión discriminada por `type`
 */
export const CredentialSchema = z.discriminatedUnion('type', [
  BitbucketCredentialSchema,
  GithubCredentialSchema,
  CloudWatchCredentialSchema,
]);

export type Credential = z.infer<typeof CredentialSchema>;

/* ============================
 * Project
 * ============================ */

const LogsRangeSchema = z.object({
  startTime: z.string().min(1),
  endTime: z.string().min(1),
});

export const ProjectSchema = z.object({
  name: z.string().min(1),
  context: z.string().min(1),
  prompts: z.array(z.string().min(1)).optional(),
  analyze: z.boolean().default(true),

  sources: z.object({
    repository: z.string().min(1),
    credentials: z.string().min(1),
  }),

  logs: z.object({
    provider: z.literal('cloudwatch'),
    logGroups: z.array(z.string().min(1)).min(1),
    credentials: z.string().min(1),
    range: LogsRangeSchema.optional(),
  }),
});

export type Project = z.infer<typeof ProjectSchema>;

/* ============================
 * Catalog
 * ============================ */

export const CatalogSchema = z.object({
  credentials: z.array(CredentialSchema),
  projects: z.array(ProjectSchema),
});

export type Catalog = z.infer<typeof CatalogSchema>;
