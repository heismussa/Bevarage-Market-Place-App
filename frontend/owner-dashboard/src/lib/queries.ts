import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "@/lib/api";
import type {
  Analytics,
  AvailabilityValue,
  Category,
  Dashboard,
  Notification,
  OrderAction,
  OrderStatusValue,
  OwnerOrderDetail,
  OwnerOrderList,
  OwnerProduct,
  OwnerStore,
  Paginated,
  PaymentStatusValue,
} from "@/lib/types";

/** Poll intervals (ms): PENDING orders 15-30s, unread notifications 30-60s. */
export const PENDING_POLL_MS = 20_000;
export const NOTIFICATION_POLL_MS = 45_000;

export const keys = {
  stores: ["owner", "stores"] as const,
  dashboard: (storeId: number) => ["owner", "dashboard", storeId] as const,
  orders: (storeId: number) => ["owner", "orders", storeId] as const,
  order: (orderId: number) => ["owner", "order", orderId] as const,
  products: (storeId: number) => ["owner", "products", storeId] as const,
  categories: ["categories"] as const,
  analytics: (storeId: number) => ["owner", "analytics", storeId] as const,
  notifications: ["notifications"] as const,
  unread: ["notifications", "unread-count"] as const,
};

/* ------------------------------- Stores ---------------------------------- */

export function useStoresQuery(enabled = true) {
  return useQuery({
    queryKey: keys.stores,
    enabled,
    queryFn: async () => {
      const page = await http.get<Paginated<OwnerStore>>("/api/v1/owner/stores/", {
        query: { page_size: 100 },
      });
      return page.results;
    },
  });
}

/* ------------------------------ Dashboard -------------------------------- */

export function useDashboard(storeId: number | undefined) {
  return useQuery({
    queryKey: keys.dashboard(storeId ?? 0),
    enabled: storeId !== undefined,
    queryFn: () =>
      http.get<Dashboard>("/api/v1/owner/stores/{id}/dashboard/", {
        path: { id: storeId! },
      }),
    refetchInterval: PENDING_POLL_MS,
  });
}

/* ------------------------------- Orders ---------------------------------- */

export type OrdersFilters = {
  status?: OrderStatusValue | "";
  payment_status?: PaymentStatusValue | "";
  search?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
};

export function useOrders(storeId: number | undefined, filters: OrdersFilters) {
  // Poll while PENDING orders could appear in the result.
  const polling = !filters.status || filters.status === "PENDING";
  return useQuery({
    queryKey: [...keys.orders(storeId ?? 0), filters],
    enabled: storeId !== undefined,
    placeholderData: keepPreviousData,
    refetchInterval: polling ? PENDING_POLL_MS : false,
    queryFn: () =>
      http.get<Paginated<OwnerOrderList>>("/api/v1/owner/stores/{id}/orders/", {
        path: { id: storeId! },
        query: {
          status: filters.status || undefined,
          payment_status: filters.payment_status || undefined,
          search: filters.search || undefined,
          date_from: filters.date_from || undefined,
          date_to: filters.date_to || undefined,
          page: filters.page,
          page_size: filters.page_size,
        },
      }),
  });
}

export function useOrder(orderId: number) {
  return useQuery({
    queryKey: keys.order(orderId),
    enabled: Number.isFinite(orderId),
    queryFn: () =>
      http.get<OwnerOrderDetail>("/api/v1/owner/orders/{id}/", {
        path: { id: orderId },
      }),
    refetchInterval: (query) =>
      query.state.data?.order_status === "PENDING" ? PENDING_POLL_MS : false,
  });
}

export function useTransitionOrder(orderId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { action: OrderAction; reason?: string }) =>
      http.post<OwnerOrderDetail>("/api/v1/owner/orders/{id}/transition/", {
        path: { id: orderId },
        body: {
          action: input.action,
          ...(input.reason ? { reason: input.reason } : {}),
        },
      }),
    onSuccess: (data) => {
      if (data && typeof data === "object" && "id" in data) {
        queryClient.setQueryData(keys.order(orderId), data);
      }
      void queryClient.invalidateQueries({ queryKey: keys.order(orderId) });
      void queryClient.invalidateQueries({ queryKey: ["owner", "orders"] });
      void queryClient.invalidateQueries({ queryKey: ["owner", "dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["owner", "products"] });
      void queryClient.invalidateQueries({ queryKey: keys.notifications });
    },
  });
}

/* ------------------------------ Products --------------------------------- */

export type ProductFilters = {
  search?: string;
  category?: number | "";
  availability?: AvailabilityValue | "";
  low_stock?: boolean;
  page?: number;
  page_size?: number;
};

export function useProducts(storeId: number | undefined, filters: ProductFilters) {
  return useQuery({
    queryKey: [...keys.products(storeId ?? 0), filters],
    enabled: storeId !== undefined,
    placeholderData: keepPreviousData,
    queryFn: () =>
      http.get<Paginated<OwnerProduct>>(
        "/api/v1/owner/stores/{store_id}/products/",
        {
          path: { store_id: storeId! },
          query: {
            search: filters.search || undefined,
            category: filters.category === "" ? undefined : filters.category,
            availability: filters.availability || undefined,
            low_stock: filters.low_stock ? true : undefined,
            page: filters.page,
            page_size: filters.page_size,
          },
        },
      ),
  });
}

export function useCategories() {
  return useQuery({
    queryKey: keys.categories,
    staleTime: 5 * 60_000,
    queryFn: async () => {
      const page = await http.get<Paginated<Category>>("/api/v1/categories/", {
        query: { page_size: 100 },
      });
      return page.results;
    },
  });
}

export function useInvalidateCatalog() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["owner", "products"] });
    void queryClient.invalidateQueries({ queryKey: ["owner", "dashboard"] });
  };
}

export function useSetStock() {
  const invalidate = useInvalidateCatalog();
  return useMutation({
    mutationFn: (input: { productId: number; stock_quantity: number }) =>
      http.patch<OwnerProduct>("/api/v1/owner/products/{id}/stock/", {
        path: { id: input.productId },
        body: { stock_quantity: input.stock_quantity },
      }),
    onSuccess: invalidate,
  });
}

export function useDeleteProduct() {
  const invalidate = useInvalidateCatalog();
  return useMutation({
    mutationFn: (productId: number) =>
      http.delete<void>("/api/v1/owner/products/{id}/", {
        path: { id: productId },
      }),
    onSuccess: invalidate,
  });
}

/* ------------------------------ Analytics -------------------------------- */

export function useAnalytics(
  storeId: number | undefined,
  range: { from: string; to: string },
) {
  return useQuery({
    queryKey: [...keys.analytics(storeId ?? 0), range],
    enabled: storeId !== undefined && Boolean(range.from) && Boolean(range.to),
    placeholderData: keepPreviousData,
    queryFn: () =>
      http.get<Analytics>("/api/v1/owner/stores/{id}/analytics/", {
        path: { id: storeId! },
        query: { from: range.from, to: range.to },
      }),
  });
}

/* ---------------------------- Notifications ------------------------------ */

export function useUnreadCount() {
  return useQuery({
    queryKey: keys.unread,
    refetchInterval: NOTIFICATION_POLL_MS,
    queryFn: async () => {
      const data = await http.get<{ unread_count: number }>(
        "/api/v1/notifications/unread-count/",
      );
      return data.unread_count;
    },
  });
}

export function useNotifications(enabled: boolean) {
  return useQuery({
    queryKey: keys.notifications,
    enabled,
    refetchInterval: enabled ? NOTIFICATION_POLL_MS : false,
    queryFn: () =>
      http.get<Paginated<Notification>>("/api/v1/notifications/", {
        query: { page_size: 10 },
      }),
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      http.post<Notification>("/api/v1/notifications/{id}/read/", {
        path: { id },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.notifications });
      void queryClient.invalidateQueries({ queryKey: keys.unread });
    },
  });
}

export function useMarkAllRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      http.post<{ updated: number }>("/api/v1/notifications/read-all/"),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.notifications });
      void queryClient.invalidateQueries({ queryKey: keys.unread });
    },
  });
}
