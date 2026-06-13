// Resolve the API base URL with three precedence rules:
//   1. `VITE_API_BASE_URL` from the environment (if set and non-empty).
//   2. In a production build (`import.meta.env.PROD`) with no explicit base,
//      default to "" so requests are issued same-origin against the FastAPI
//      server that is also serving the built frontend.
//   3. In dev mode (Vite dev server on :5173) with no explicit base, default
//      to the local FastAPI dev server on :8000.
const DEV_DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

const explicitBase = (import.meta.env.VITE_API_BASE_URL ?? "").trim();
let resolvedBase: string;
if (explicitBase !== "") {
  resolvedBase = explicitBase;
} else if (import.meta.env.PROD) {
  resolvedBase = "";
} else {
  resolvedBase = DEV_DEFAULT_API_BASE_URL;
}

export const API_BASE_URL = resolvedBase.replace(/\/+$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly url: string;

  constructor(status: number, detail: string, url: string) {
    super(`API request failed (${status}) for ${url}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.url = url;
  }
}

export type QueryValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | Array<string | number | boolean | null | undefined>;

function buildUrl(path: string, params?: Record<string, QueryValue>): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const search = new URLSearchParams();
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null) continue;
      if (Array.isArray(value)) {
        for (const item of value) {
          if (item === undefined || item === null) continue;
          search.append(key, String(item));
        }
      } else {
        search.set(key, String(value));
      }
    }
  }
  const queryString = search.toString();
  const pathWithQuery = queryString
    ? `${normalizedPath}?${queryString}`
    : normalizedPath;
  // When API_BASE_URL is empty (production same-origin) the browser resolves
  // the relative URL against window.location. When set, prefix it directly.
  return API_BASE_URL ? `${API_BASE_URL}${pathWithQuery}` : pathWithQuery;
}

async function extractDetail(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";
  try {
    if (contentType.includes("application/json")) {
      const body = (await response.json()) as { detail?: unknown };
      if (body && typeof body.detail === "string") return body.detail;
      return JSON.stringify(body);
    }
    return await response.text();
  } catch {
    return response.statusText || "Unknown error";
  }
}

export interface RequestOptions {
  params?: Record<string, QueryValue>;
  body?: unknown;
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

async function request<T>(
  method: "GET" | "POST",
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const url = buildUrl(path, options.params);
  const init: RequestInit = {
    method,
    headers: {
      Accept: "application/json",
      ...(options.body !== undefined
        ? { "Content-Type": "application/json" }
        : {}),
      ...options.headers,
    },
    signal: options.signal,
  };
  if (options.body !== undefined) {
    init.body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(url, init);
  } catch (cause) {
    const message = cause instanceof Error ? cause.message : String(cause);
    throw new ApiError(0, `Network error: ${message}`, url);
  }

  if (!response.ok) {
    const detail = await extractDetail(response);
    throw new ApiError(response.status, detail, url);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function apiGet<T>(
  path: string,
  params?: Record<string, QueryValue>,
  signal?: AbortSignal,
): Promise<T> {
  return request<T>("GET", path, { params, signal });
}

export function apiPost<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  return request<T>("POST", path, { body, signal });
}
