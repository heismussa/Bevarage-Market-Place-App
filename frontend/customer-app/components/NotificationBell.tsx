import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { Pressable, Text, View } from "react-native";

import { api, unwrap } from "@/lib/api";
import { POLL, keys } from "@/lib/query";

export function useUnreadCount(): number {
  const { data } = useQuery({
    queryKey: keys.unreadCount,
    queryFn: async () => unwrap(await api.GET("/api/v1/notifications/unread-count/")),
    refetchInterval: POLL.unread,
    select: (value) => value.unread_count,
  });
  return data ?? 0;
}

export function NotificationBell() {
  const router = useRouter();
  const unread = useUnreadCount();

  return (
    <Pressable
      onPress={() => router.push("/notifications")}
      hitSlop={8}
      accessibilityRole="button"
      accessibilityLabel={`Notifications, ${unread} unread`}
      className="h-10 w-10 items-center justify-center rounded-full bg-surface"
    >
      <Ionicons name="notifications-outline" size={22} color="#FFFFFF" />
      {unread > 0 ? (
        <View className="absolute -right-0.5 -top-0.5 min-w-[18px] items-center rounded-full bg-danger px-1">
          <Text className="text-[11px] font-bold text-background">
            {unread > 99 ? "99+" : unread}
          </Text>
        </View>
      ) : null}
    </Pressable>
  );
}
