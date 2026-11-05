import { useInfiniteQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useState } from "react";
import { FlatList } from "react-native";

import { ChipRow } from "@/components/Chip";
import { OrderCard } from "@/components/OrderCard";
import { Screen } from "@/components/Screen";
import { EmptyState, ErrorView, LoadingView } from "@/components/StateViews";
import { api, unwrap } from "@/lib/api";
import { flattenPages, keys, nextPageParam } from "@/lib/query";
import type { OrderList, OrderStatusValue } from "@/lib/types";

const FILTERS: { value: OrderStatusValue | null; label: string }[] = [
  { value: null, label: "All" },
  { value: "PENDING", label: "Pending" },
  { value: "ACCEPTED", label: "Accepted" },
  { value: "PREPARING", label: "Preparing" },
  { value: "READY", label: "Ready" },
  { value: "COMPLETED", label: "Completed" },
  { value: "REJECTED", label: "Rejected" },
  { value: "CANCELLED", label: "Cancelled" },
];

export default function OrdersScreen() {
  const router = useRouter();
  const [status, setStatus] = useState<OrderStatusValue | null>(null);

  const query = useInfiniteQuery({
    queryKey: keys.orders(status),
    initialPageParam: 1,
    queryFn: async ({ pageParam }) =>
      unwrap(
        await api.GET("/api/v1/orders/", {
          params: {
            query: {
              page: pageParam,
              page_size: 20,
              status: status ?? undefined,
            },
          },
        }),
      ),
    getNextPageParam: nextPageParam,
  });

  const orders = flattenPages<OrderList>(query.data);

  return (
    <Screen title="Orders" scroll={false} padded={false} refreshing={query.isRefetching} onRefresh={() => void query.refetch()}>
      <FlatList
        data={orders}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 32 }}
        onEndReached={() => {
          if (query.hasNextPage && !query.isFetchingNextPage) void query.fetchNextPage();
        }}
        ListHeaderComponent={
          <ChipRow options={FILTERS} value={status} onChange={setStatus} />
        }
        renderItem={({ item }) => (
          <OrderCard order={item} onPress={() => router.push(`/order/${item.id}`)} />
        )}
        ListEmptyComponent={
          query.isLoading ? (
            <LoadingView />
          ) : query.isError ? (
            <ErrorView error={query.error} onRetry={() => void query.refetch()} />
          ) : (
            <EmptyState icon="receipt-outline" title="No orders yet" message="Your past orders will show up here." />
          )
        }
      />
    </Screen>
  );
}
