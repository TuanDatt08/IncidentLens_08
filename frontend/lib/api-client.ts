import { API_BASE_URL, AUTH_ENABLED } from "./config";

let csrfToken: string | undefined;
let authenticated = false;
let generation = 0;
const requests = new Set<AbortController>();

export function setSessionTransport(token?: string) {
  csrfToken = token;
  authenticated = Boolean(token);
  generation += 1;
  for (const controller of requests) controller.abort();
  requests.clear();
}

export function isSessionReady() { return !AUTH_ENABLED || authenticated; }

export type UploadRequestOptions = {
  signal?: AbortSignal;
  onProgress?: (loaded: number, total?: number) => void;
  onUploaded?: () => void;
};

// Only multipart uploads use XHR, because fetch has no browser upload progress.
export function apiUpload<T>(path: string, body: FormData, options: UploadRequestOptions = {}): Promise<T> {
  if (AUTH_ENABLED && !authenticated) return Promise.reject(new ApiError("Sign in again to continue. Your selected files are kept.", 401, "AUTHENTICATION_REQUIRED"));
  const requestGeneration = generation;
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const controller = new AbortController();
    let settled = false;
    const finish = (error?: unknown, value?: T) => {
      if (settled) return;
      settled = true;
      requests.delete(controller);
      options.signal?.removeEventListener("abort", abort);
      controller.signal.removeEventListener("abort", abort);
      xhr.onload = xhr.onerror = xhr.onabort = xhr.ontimeout = null;
      xhr.upload.onprogress = xhr.upload.onload = null;
      if (error) reject(error); else resolve(value as T);
    };
    const abort = () => {
      finish(new DOMException("Upload cancelled.", "AbortError"));
      xhr.abort();
    };
    requests.add(controller);
    controller.signal.addEventListener("abort", abort, { once: true });
    options.signal?.addEventListener("abort", abort, { once: true });
    if (options.signal?.aborted) { abort(); return; }
    xhr.upload.onprogress = (event) => {
      if (!settled) options.onProgress?.(event.loaded, event.lengthComputable ? event.total : undefined);
    };
    xhr.upload.onload = () => { if (!settled) options.onUploaded?.(); };
    xhr.onerror = () => finish(new TypeError("Upload failed because of a network error. Please try again."));
    xhr.ontimeout = () => finish(new Error("Upload timed out. Please try again."));
    xhr.onabort = () => finish(new DOMException("Upload cancelled.", "AbortError"));
    xhr.onload = () => {
      void (async () => {
        try {
          if (settled) return;
          if (requestGeneration !== generation) throw new ApiError("Session changed. Try uploading again after signing in.", 401);
          if (xhr.status < 200 || xhr.status >= 300) {
            const error = await parseApiError(new Response(xhr.responseText, { status: xhr.status }));
            if (settled) return;
            if (requestGeneration !== generation) throw new ApiError("Session changed. Try uploading again after signing in.", 401);
            if (AUTH_ENABLED && (xhr.status === 401 && error.code === "AUTHENTICATION_REQUIRED" && authenticated || xhr.status === 403 && error.code === "PASSWORD_CHANGE_REQUIRED")) window.dispatchEvent(new Event("auth:expired"));
            throw error;
          }
          finish(undefined, JSON.parse(xhr.responseText) as T);
        } catch (error) { finish(error); }
      })();
    };
    try {
      xhr.open("POST", API_BASE_URL + path);
      // Same-origin cookies are automatic. The browser supplies multipart boundaries.
      if (AUTH_ENABLED && csrfToken) xhr.setRequestHeader("X-CSRF-Token", csrfToken);
      xhr.send(body);
    } catch (error) { finish(error); }
  });
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  if (!AUTH_ENABLED) {
    const headers = new Headers(init?.headers);
    if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    return fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  }
  const isAuth = path.startsWith("/auth/");
  if (!isAuth && !authenticated) throw new ApiError("Sign in again to continue. Your draft is kept in memory.", 401, "AUTHENTICATION_REQUIRED");
  const requestGeneration = generation;
  const controller = new AbortController();
  requests.add(controller);
  const abort = () => controller.abort();
  if (init?.signal?.aborted) controller.abort();
  else init?.signal?.addEventListener("abort", abort, { once: true });
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !(init.body instanceof Blob)) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes((init?.method ?? "GET").toUpperCase()) && csrfToken) headers.set("X-CSRF-Token", csrfToken);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers, credentials: "same-origin", cache: "no-store", signal: controller.signal });
    if (requestGeneration !== generation) throw new ApiError("Session changed. Reload the data before continuing.", 401);
    if (response.status === 401 && path !== "/auth/login") {
      const error = await parseApiError(response);
      if (error.code === "AUTHENTICATION_REQUIRED" && authenticated) window.dispatchEvent(new Event("auth:expired"));
      throw error;
    }
    if (response.status === 403 && !isAuth) {
      const copy = response.clone();
      const error = await parseApiError(copy);
      if (error.code === "PASSWORD_CHANGE_REQUIRED") window.dispatchEvent(new Event("auth:expired"));
    }
    return response;
  } finally { requests.delete(controller); init?.signal?.removeEventListener("abort", abort); }
}

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
  const response = await apiFetch(path, init);

  if (!response.ok) {
    throw await parseApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
