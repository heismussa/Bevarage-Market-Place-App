import {
  createApiClient,
  createWebTokenStore,
  resolveApiBaseUrl,
  setTokenStore,
} from "@beverage/api";

setTokenStore(createWebTokenStore("beverage_owner"));

export const api = createApiClient({
  baseUrl: resolveApiBaseUrl(import.meta.env.VITE_API_URL),
  onSessionExpired: () => {
    window.dispatchEvent(new CustomEvent("beverage:session-expired"));
  },
});
