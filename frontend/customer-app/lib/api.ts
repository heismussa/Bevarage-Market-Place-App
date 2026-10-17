import {
  createApiClient,
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

export const api = createApiClient({
  baseUrl: resolveApiBaseUrl(process.env.EXPO_PUBLIC_API_URL),
});
