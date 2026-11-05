import { ApiError } from "@beverage/api";
import { QueryClient, focusManager } from "@tanstack/react-query";
import { AppState, Platform } from "react-native";

/** Polling cadences from the backend conventions. */
export const POLL = {
  payment: 3_000,
  order: 15_000,
  orders: 30_000,
  unread: 45_000,
} as const;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status > 0 && error.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
    },
  },
});

/** Pause polling while the app is backgrounded. */
if (Platform.OS !== "web") {
  focusManager.setEventListener((handleFocus) => {
    const subscription = AppState.addEventListener("change", (state) => {
      handleFocus(state === "active");
    });
    return () => subscription.remove();
  });
}

/** Flatten `useInfiniteQuery` pages of a DRF paginated response. */
export function flattenPages<T>(
  data: { pages: { results: T[] }[] } | undefined,
): T[] {
  return data ? data.pages.flatMap((page) => page.results) : [];
}

/** `getNextPageParam` for DRF page-number pagination. */
export function nextPageParam(
  last: { next?: string | null },
  pages: unknown[],
): number | undefined {
  return last.next ? pages.length + 1 : undefined;
}

export const keys = {
  cart: ["cart"] as const,
  categories: ["categories"] as const,
  me: ["me"] as const,
  unreadCount: ["notifications", "unread-count"] as const,
  notifications: ["notifications", "list"] as const,
  addresses: ["addresses"] as const,
  address: (id: number) => ["addresses", id] as const,
  orders: (status: string | null) => ["orders", status ?? "all"] as const,
  ordersRoot: ["orders"] as const,
  order: (id: number) => ["order", id] as const,
  payment: (orderId: number) => ["order", orderId, "payment"] as const,
  store: (id: number) => ["store", id] as const,
  storeProducts: (id: number, search: string, category: number | null) =>
    ["store", id, "products", search, category] as const,
  product: (id: number) => ["product", id] as const,
  stores: (params: unknown) => ["stores", params] as const,
  popular: (category: number | null) => ["popular", category] as const,
};
