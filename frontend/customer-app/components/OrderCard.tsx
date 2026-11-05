import { formatDateTime, formatMoney } from "@beverage/api";
import { Pressable, Text, View } from "react-native";

import type { OrderList } from "@/lib/types";

import { OrderStatusBadge, PaymentStatusBadge } from "./StatusBadge";

export function OrderCard({
  order,
  onPress,
}: {
  order: OrderList;
  onPress: () => void;
}) {
  // The list payload has no payment method, so only show states that read the same for cash and mobile.
  const showPayment = order.payment_status !== "PENDING" && order.payment_status !== "CANCELLED";
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      className="mb-3 rounded-2xl border border-border bg-surface p-4 active:opacity-80"
    >
      <View className="flex-row items-start justify-between">
        <View className="mr-2 flex-1">
          <Text className="text-base font-semibold text-foreground">
            #{order.order_number}
          </Text>
          <Text numberOfLines={1} className="mt-0.5 text-sm text-muted">
            {order.store.store_name}
          </Text>
        </View>
        <OrderStatusBadge status={order.order_status} />
      </View>

      <View className="mt-3 flex-row items-center justify-between">
        <Text className="text-xs text-muted">
          {order.item_count} {order.item_count === 1 ? "item" : "items"} ·{" "}
          {formatDateTime(order.ordered_at)}
        </Text>
        <Text className="text-base font-bold text-foreground">
          {formatMoney(order.total_amount)}
        </Text>
      </View>

      {showPayment ? (
        <View className="mt-2">
          <PaymentStatusBadge status={order.payment_status} isCash={false} />
        </View>
      ) : null}
    </Pressable>
  );
}
