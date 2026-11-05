import {
  ApiError,
  createApiClient,
  createWebTokenStore,
  getTokenStore,
  messageForCode,
  parseApiError,
  resolveApiBaseUrl,
  setTokenStore,
} from "@beverage/api";

setTokenStore(createWebTokenStore("beverage_owner"));

const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_URL);

/** Origin without the /api/v1 suffix; schema paths already include it. */
export const API_ORIGIN = API_BASE_URL.replace(/\/api\/v1\/?$/, "").replace(
  /\/$/,
  "",
);

export const api = createApiClient({
  baseUrl: API_BASE_URL,
  onSessionExpired: () => {
    window.dispatchEvent(new CustomEvent("beverage:session-expired"));
  },
});

/* -------------------------------------------------------------------------- */
/* Thin untyped wrappers. Response shapes live in src/lib/types.ts.            */
/* openapi-fetch errors are thrown by the shared middleware as ApiError.       */
/* -------------------------------------------------------------------------- */

type Query = Record<string, string | number | boolean | null | undefined>;

export type RequestOptions = {
  path?: Record<string, string | number>;
  query?: Query;
  body?: unknown;
};

type RawInit = {
  params?: { path?: Record<string, string | number>; query?: Query };
  body?: unknown;
  bodySerializer?: (body: unknown) => unknown;
};

type RawFn = (
  path: string,
  init?: RawInit,
) => Promise<{ data?: unknown; response: Response }>;

const raw = api as unknown as Record<"GET" | "POST" | "PATCH" | "DELETE", RawFn>;

async function call<T>(
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const init: RawInit = {
    params: { path: options.path, query: options.query },
  };
  if (options.body !== undefined) {
    init.body = options.body;
    if (typeof FormData !== "undefined" && options.body instanceof FormData) {
      // Let the browser set the multipart boundary.
      init.bodySerializer = (body) => body;
    }
  }
  const { data } = await raw[method](path, init);
  return data as T;
}

export const http = {
  get: <T>(path: string, options?: RequestOptions) => call<T>("GET", path, options),
  post: <T>(path: string, options?: RequestOptions) => call<T>("POST", path, options),
  patch: <T>(path: string, options?: RequestOptions) =>
    call<T>("PATCH", path, options),
  delete: <T>(path: string, options?: RequestOptions) =>
    call<T>("DELETE", path, options),
};

/** Human message for any thrown value. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const details = error.details;
    if (error.code === "VALIDATION_ERROR" && details && typeof details === "object") {
      const first = Object.values(details).find(
        (value) => typeof value === "string" || Array.isArray(value),
      );
      const text = Array.isArray(first) ? first[0] : first;
      if (typeof text === "string" && text) return text;
    }
    return messageForCode(error.code, error.message);
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}

/**
 * Download the store's orders as CSV with the Bearer token.
 * Do not send Accept: text/csv. Leave Accept unset so the browser default applies.
 */
export async function downloadOrdersCsv(
  storeId: number,
  query: Query,
): Promise<string> {
  // A cheap authenticated call first: the client refreshes an expired access token for us.
  await http.get("/api/v1/auth/me/");
  const access = await getTokenStore().getAccess();

  const url = new URL(`${API_ORIGIN}/api/v1/owner/stores/${storeId}/orders/export/`);
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }

  const response = await fetch(url.toString(), {
    method: "GET",
    headers: access ? { Authorization: `Bearer ${access}` } : {},
  });

  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }
    throw parseApiError(response.status, body);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  const filename = match?.[1]
    ? decodeURIComponent(match[1])
    : `orders-store-${storeId}.csv`;

  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
  return filename;
}
