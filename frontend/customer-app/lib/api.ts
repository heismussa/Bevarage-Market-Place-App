import {
  ApiError,
  createApiClient,
  getTokenStore,
  resolveApiBaseUrl,
  setTokenStore,
  type TokenPair,
  type TokenStore,
} from "@beverage/api";
import * as SecureStore from "expo-secure-store";

const ACCESS_KEY = "beverage_customer_access";
const REFRESH_KEY = "beverage_customer_refresh";

const secureTokenStore: TokenStore = {
  getAccess: () => SecureStore.getItemAsync(ACCESS_KEY),
  getRefresh: () => SecureStore.getItemAsync(REFRESH_KEY),
  setTokens: async ({ access, refresh }: TokenPair) => {
    await SecureStore.setItemAsync(ACCESS_KEY, access);
    await SecureStore.setItemAsync(REFRESH_KEY, refresh);
  },
  clear: async () => {
    await SecureStore.deleteItemAsync(ACCESS_KEY);
    await SecureStore.deleteItemAsync(REFRESH_KEY);
  },
};

setTokenStore(secureTokenStore);

type Listener = () => void;
const sessionExpiredListeners = new Set<Listener>();

/** Subscribe to "refresh failed, log in again". Returns an unsubscribe function. */
export function onSessionExpired(listener: Listener): () => void {
  sessionExpiredListeners.add(listener);
  return () => {
    sessionExpiredListeners.delete(listener);
  };
}

/**
 * Typed openapi-fetch client. Non-2xx responses throw `ApiError`
 * (shape `{error:{code,message,details}}`), so `data` is set on success.
 */
export const api = createApiClient({
  baseUrl: resolveApiBaseUrl(process.env.EXPO_PUBLIC_API_URL),
  onSessionExpired: () => {
    sessionExpiredListeners.forEach((listener) => listener());
  },
});

export async function saveTokens(tokens: TokenPair): Promise<void> {
  await getTokenStore().setTokens(tokens);
}

export async function clearTokens(): Promise<void> {
  await getTokenStore().clear();
}

export async function hasStoredTokens(): Promise<boolean> {
  const access = await getTokenStore().getAccess();
  const refresh = await getTokenStore().getRefresh();
  return Boolean(access || refresh);
}

/** Return `data` or throw; non-2xx already throws ApiError from the client middleware. */
export function unwrap<T>(result: { data?: T }): T {
  if (result.data === undefined) {
    throw new ApiError("INTERNAL_ERROR", "Unexpected empty response.", 0);
  }
  return result.data;
}
