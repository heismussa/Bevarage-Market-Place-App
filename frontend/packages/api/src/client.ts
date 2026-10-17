import createClient, { type Middleware } from "openapi-fetch";

import type { paths } from "./schema";
import { ApiError, isApiErrorBody, parseApiError } from "./errors";
import { getTokenStore, type TokenPair } from "./tokens";

export type ApiClient = ReturnType<typeof createClient<paths>>;

export type CreateApiClientOptions = {
  /** Base URL including /api/v1, e.g. http://localhost:8000/api/v1 */
  baseUrl: string;
  /** Called when refresh fails and the user must log in again. */
  onSessionExpired?: () => void;
};

let refreshPromise: Promise<TokenPair | null> | null = null;

async function readJsonSafe(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

async function refreshAccessToken(baseUrl: string): Promise<TokenPair | null> {
  const store = getTokenStore();
  const refresh = await store.getRefresh();
  if (!refresh) return null;

  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ refresh }),
  });

  const body = await readJsonSafe(response);
  if (!response.ok) {
    await store.clear();
    return null;
  }

  const data = body as { access?: string; refresh?: string };
  if (!data.access) {
    await store.clear();
    return null;
  }

  const tokens: TokenPair = {
    access: data.access,
    refresh: data.refresh ?? refresh,
  };
  await store.setTokens(tokens);
  return tokens;
}

function singleFlightRefresh(baseUrl: string): Promise<TokenPair | null> {
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken(baseUrl).finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

function isTokenInvalid(status: number, body: unknown): boolean {
  return (
    status === 401 &&
    isApiErrorBody(body) &&
    body.error.code === "TOKEN_INVALID"
  );
}

/**
 * Typed OpenAPI client with Bearer auth and one-shot refresh on TOKEN_INVALID.
 */
export function createApiClient(options: CreateApiClientOptions): ApiClient {
  const baseUrl = options.baseUrl.replace(/\/$/, "");
  const client = createClient<paths>({ baseUrl });

  const middleware: Middleware = {
    async onRequest({ request }) {
      const store = getTokenStore();
      const access = await store.getAccess();
      if (access) {
        request.headers.set("Authorization", `Bearer ${access}`);
      }
      if (!request.headers.has("Accept")) {
        request.headers.set("Accept", "application/json");
      }
      return request;
    },

    async onResponse({ request, response }) {
      if (response.ok) return response;

      const clone = response.clone();
      const body = await readJsonSafe(clone);

      const url = new URL(request.url);
      const isAuthPath =
        url.pathname.includes("/auth/login/") ||
        url.pathname.includes("/auth/refresh/") ||
        url.pathname.includes("/auth/register/") ||
        url.pathname.includes("/auth/password/reset");

      if (!isAuthPath && isTokenInvalid(response.status, body)) {
        const alreadyRetried = request.headers.get("X-Retry-After-Refresh");
        if (!alreadyRetried) {
          const tokens = await singleFlightRefresh(baseUrl);
          if (tokens) {
            const retryHeaders = new Headers(request.headers);
            retryHeaders.set("Authorization", `Bearer ${tokens.access}`);
            retryHeaders.set("X-Retry-After-Refresh", "1");
            return fetch(
              new Request(request, {
                headers: retryHeaders,
              }),
            );
          }
          options.onSessionExpired?.();
        } else {
          await getTokenStore().clear();
          options.onSessionExpired?.();
        }
      }

      throw parseApiError(response.status, body);
    },
  };

  client.use(middleware);
  return client;
}

/**
 * Resolve the API base URL. Apps should pass EXPO_PUBLIC_API_URL or VITE_API_URL.
 */
export function resolveApiBaseUrl(explicit?: string | null): string {
  if (explicit && explicit.trim()) {
    return explicit.replace(/\/$/, "");
  }
  return "http://localhost:8000/api/v1";
}

export { ApiError };
