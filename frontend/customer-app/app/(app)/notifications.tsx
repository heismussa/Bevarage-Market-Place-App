import { formatDateTime } from "@beverage/api";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { Pressable, Text, View } from "react-native";

import { Button } from "@/components/Button";
import { Screen } from "@/components/Screen";
import { EmptyState, ErrorView, LoadingView } from "@/components/StateViews";
import { api, unwrap } from "@/lib/api";
import { flattenPages, keys, nextPageParam, POLL } from "@/lib/query";
import type { Notification } from "@/lib/types";

export default function NotificationsScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const unreadQuery = useQuery({
    queryKey: keys.unreadCount,
    queryFn: async () => unwrap(await api.GET("/api/v1/notifications/unread-count/")),
    refetchInterval: POLL.unread,
  });

  const query = useInfiniteQuery({
    queryKey: keys.notifications,
    initialPageParam: 1,
    queryFn: async ({ pageParam }) =>
      unwrap(
        await api.GET("/api/v1/notifications/", {
          params: { query: { page: pageParam, page_size: 20 } },
        }),
      ),
    getNextPageParam: nextPageParam,
  });

  const markAll = useMutation({
    mutationFn: async () => unwrap(await api.POST("/api/v1/notifications/read-all/")),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.notifications });
      void queryClient.invalidateQueries({ queryKey: keys.unreadCount });
    },
  });

  const markOne = useMutation({
    mutationFn: async (id: number) =>
      unwrap(await api.POST("/api/v1/notifications/{id}/read/", { params: { path: { id } } })),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.notifications });
      void queryClient.invalidateQueries({ queryKey: keys.unreadCount });
    },
  });

  const items = flattenPages<Notification>(query.data);
  const unread = unreadQuery.data?.unread_count ?? 0;

  const open = (item: Notification) => {
    if (!item.is_read) void markOne.mutateAsync(item.id);
    if (item.order) router.push(`/order/${item.order}`);
  };

  return (
    <Screen
      title="Notifications"
      back
      refreshing={query.isRefetching}
      onRefresh={() => void query.refetch()}
    >
      {unread > 0 ? (
        <Button
          title={`Mark all as read (${unread})`}
          variant="ghost"
          className="mb-3"
          loading={markAll.isPending}
          onPress={() => void markAll.mutateAsync()}
        />
      ) : null}
      {query.isLoading ? <LoadingView /> : null}
      {query.isError ? (
        <ErrorView error={query.error} onRetry={() => void query.refetch()} />
      ) : null}
      {!query.isLoading && items.length === 0 ? (
        <EmptyState icon="notifications-outline" title="You're all caught up" />
      ) : null}
      {items.map((item) => (
        <Pressable
          key={item.id}
          onPress={() => open(item)}
          className={`mb-2 rounded-2xl border p-4 ${
            item.is_read ? "border-border bg-surface" : "border-primary/40 bg-primary/10"
          }`}
        >
          <View className="flex-row items-start justify-between gap-3">
            <View className="flex-1">
              <Text className="font-semibold text-foreground">{item.title}</Text>
              <Text className="mt-1 text-sm text-muted">{item.message}</Text>
            </View>
            <Text className="text-xs text-muted">{formatDateTime(item.created_at)}</Text>
          </View>
        </Pressable>
      ))}
      {query.hasNextPage ? (
        <Button
          title="Load more"
          variant="ghost"
          className="mt-2"
          loading={query.isFetchingNextPage}
          onPress={() => void query.fetchNextPage()}
        />
      ) : null}
    </Screen>
  );
}
