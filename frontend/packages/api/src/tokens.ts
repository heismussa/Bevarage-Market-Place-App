/**
 * Token storage adapters. The customer app uses SecureStore; the owner dashboard
 * uses localStorage. Inject the adapter once at app start.
 */

export type TokenPair = {
  access: string;
  refresh: string;
};

export type TokenStore = {
  getAccess: () => Promise<string | null> | string | null;
  getRefresh: () => Promise<string | null> | string | null;
  setTokens: (tokens: TokenPair) => Promise<void> | void;
  clear: () => Promise<void> | void;
};

let store: TokenStore | null = null;

export function setTokenStore(next: TokenStore): void {
  store = next;
}

export function getTokenStore(): TokenStore {
  if (!store) {
    throw new Error(
      "Token store is not configured. Call setTokenStore(...) at app startup.",
    );
  }
  return store;
}

/** Browser localStorage adapter for the owner dashboard. */
export function createWebTokenStore(prefix = "beverage"): TokenStore {
  const accessKey = `${prefix}_access`;
  const refreshKey = `${prefix}_refresh`;
  return {
    getAccess: () =>
      typeof localStorage === "undefined" ? null : localStorage.getItem(accessKey),
    getRefresh: () =>
      typeof localStorage === "undefined" ? null : localStorage.getItem(refreshKey),
    setTokens: ({ access, refresh }) => {
      localStorage.setItem(accessKey, access);
      localStorage.setItem(refreshKey, refresh);
    },
    clear: () => {
      localStorage.removeItem(accessKey);
      localStorage.removeItem(refreshKey);
    },
  };
}

/** In-memory adapter for tests. */
export function createMemoryTokenStore(
  initial: Partial<TokenPair> = {},
): TokenStore {
  let access = initial.access ?? null;
  let refresh = initial.refresh ?? null;
  return {
    getAccess: () => access,
    getRefresh: () => refresh,
    setTokens: (tokens) => {
      access = tokens.access;
      refresh = tokens.refresh;
    },
    clear: () => {
      access = null;
      refresh = null;
    },
  };
}
