import { API_BASE_URL } from "./config";

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly code?: string, readonly details?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

export async function parseApiError(response: Response): Promise<ApiError> {
  let message = "The request could not be completed.";
  let code: string | undefined;
  let details: unknown;
  try {
    const body = await response.json() as {
      error?: { code?: unknown; message?: unknown; details?: unknown };
      detail?: unknown;
      message?: unknown;
    };
    const apiError = body?.error;
    if (typeof apiError?.message === "string") message = apiError.message;
    else if (typeof body?.detail === "string") message = body.detail;
    else if (typeof body?.message === "string") message = body.message;
    if (typeof apiError?.code === "string") code = apiError.code;
    details = apiError?.details;
  } catch {
    // Keep the generic message when the API does not return JSON.
  }
  return new ApiError(message, response.status, code, details);
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
