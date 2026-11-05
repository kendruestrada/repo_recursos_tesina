import { z } from 'zod';

export const BackendProjectSchema = z.object({
  id: z.string().min(1),
  projectName: z.string().min(1),
  global: z.boolean(),
});

export type BackendProject = z.infer<typeof BackendProjectSchema>;

export const BackendProjectRepositorySchema = z.object({
  repoSlug: z.string().min(1),
  isOutdated: z.boolean(),
});

export type BackendProjectRepository = z.infer<
  typeof BackendProjectRepositorySchema
>;

export const BackendProjectBehindRemoteSchema =
  BackendProjectSchema.extend({
    isBehindRemote: z.boolean(),
    repositories: z.array(BackendProjectRepositorySchema),
  });

export type BackendProjectBehindRemote = z.infer<
  typeof BackendProjectBehindRemoteSchema
>;
