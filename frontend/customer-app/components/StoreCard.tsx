import { formatMoney } from "@beverage/api";
import { Ionicons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";

import { formatDistance } from "@/lib/format";
import type { PublicStore } from "@/lib/types";

import { RemoteImage } from "./RemoteImage";
import { Badge } from "./StatusBadge";

export function StoreCard({
  store,
  onPress,
}: {
  store: PublicStore;
  onPress: () => void;
}) {
  const distance = formatDistance(store.distance_km);
  const place = [store.area, store.city].filter(Boolean).join(", ") || store.location;
  const open = store.status === "OPEN";

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      className="mb-3 flex-row rounded-2xl border border-border bg-surface p-3 active:opacity-80"
    >
      <RemoteImage uri={store.logo} size={72} icon="storefront-outline" />
      <View className="ml-3 flex-1">
        <View className="flex-row items-start justify-between">
          <Text numberOfLines={1} className="mr-2 flex-1 text-base font-semibold text-foreground">
            {store.store_name}
          </Text>
          <Badge label={open ? "Open" : "Closed"} tone={open ? "success" : "danger"} />
        </View>
        <View className="mt-1 flex-row items-center">
          <Ionicons name="location-outline" size={14} color="#7DA0CA" />
          <Text numberOfLines={1} className="ml-1 flex-1 text-sm text-muted">
            {place}
          </Text>
        </View>
        <View className="mt-1 flex-row items-center">
          {distance ? (
            <Text className="mr-3 text-xs text-muted">{distance} away</Text>
          ) : null}
          <Text className="text-xs text-muted">
            Delivery {formatMoney(store.delivery_fee)}
          </Text>
        </View>
      </View>
    </Pressable>
  );
}
