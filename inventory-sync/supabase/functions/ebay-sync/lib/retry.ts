// Small retry-with-backoff helper shared by the eBay HTTP client.

export interface RetryOptions {
  maxAttempts: number;
  baseDelayMs: number;
  /** Return true if the error/status is worth retrying (network blip, 429, 5xx). */
  isRetryable: (error: unknown) => boolean;
}

const DEFAULT_OPTIONS: RetryOptions = {
  maxAttempts: 3,
  baseDelayMs: 500,
  isRetryable: () => true,
};

export class RetryExhaustedError extends Error {
  constructor(public readonly attempts: number, public readonly cause: unknown) {
    super(`Retry exhausted after ${attempts} attempts: ${String(cause)}`);
    this.name = "RetryExhaustedError";
  }
}

export async function withRetry<T>(
  fn: () => Promise<T>,
  options: Partial<RetryOptions> = {},
): Promise<T> {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  let lastError: unknown;

  for (let attempt = 1; attempt <= opts.maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      const isLastAttempt = attempt === opts.maxAttempts;
      if (isLastAttempt || !opts.isRetryable(error)) {
        break;
      }
      const delay = opts.baseDelayMs * 2 ** (attempt - 1);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw new RetryExhaustedError(opts.maxAttempts, lastError);
}

/** HTTP errors carrying a status code, thrown by the eBay client below. */
export class HttpStatusError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "HttpStatusError";
  }
}

export function isRetryableHttpError(error: unknown): boolean {
  if (error instanceof HttpStatusError) {
    return error.status === 429 || error.status >= 500;
  }
  // Network-level failures (DNS, connection reset, timeout) surface as
  // plain TypeError/DOMException from fetch — treat those as retryable too.
  return true;
}
