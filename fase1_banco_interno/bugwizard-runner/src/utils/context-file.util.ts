import { createHash } from 'crypto';

export interface ContextFile {
  filename: string;
  mimetype: string;
  size: number;
  checksum: string;
  totalParts: number;
  partNumber: number;
}

export interface ContextFileWithData extends ContextFile {
  data: string;
}

function toBase64(input: string): string {
  return Buffer.from(input, 'utf-8').toString('base64');
}

function md5(input: string): string {
  return createHash('md5').update(input).digest('hex');
}

export function buildContextFile(
  content: string,
  options?: {
    filename?: string;
    mimetype?: string;
  }
): {
  withData: ContextFileWithData;
  withoutData: ContextFile;
} {
  const base64 = toBase64(content);
  const checksum = md5(base64);

  const base: ContextFile = {
    filename: options?.filename ?? 'context.txt',
    mimetype: options?.mimetype ?? 'text/plain',
    size: base64.length,
    checksum,
    totalParts: 1,
    partNumber: 1,
  };

  return {
    withData: {
      ...base,
      data: base64,
    },
    withoutData: base,
  };
}
