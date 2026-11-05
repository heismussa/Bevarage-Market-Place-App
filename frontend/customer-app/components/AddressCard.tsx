import { formatPhoneDisplay } from "@beverage/api";
import { Ionicons } from "@expo/vector-icons";
import type { ReactNode } from "react";
import { Pressable, Text, View } from "react-native";

import type { Address } from "@/lib/types";

import { Badge } from "./StatusBadge";

export function addressSummary(address: Address): string {
  return [address.address_line, address.area, address.city].filter(Boolean).join(", ");
}

export function AddressCard({
  address,
  selected,
  onPress,
  actions,
}: {
  address: Address;
  selected?: boolean;
  onPress?: () => void;
  actions?: ReactNode;
}) {
  const content = (
    <View
      className={`mb-3 rounded-2xl border bg-surface p-4 ${
        selected ? "border-primary" : "border-border"
      }`}
    >
      <View className="flex-row items-center">
        {selected !== undefined ? (
          <Ionicons
            name={selected ? "radio-button-on" : "radio-button-off"}
            size={20}
            color={selected ? "#C1E8FF" : "#7DA0CA"}
          />
        ) : null}
        <Text
          className={`flex-1 text-base font-semibold text-foreground ${
            selected !== undefined ? "ml-2" : ""
          }`}
        >
          {address.address_name}
        </Text>
        {address.is_default ? <Badge label="Default" tone="success" /> : null}
      </View>
      <Text className="mt-1 text-sm text-muted">{addressSummary(address)}</Text>
      <Text className="mt-0.5 text-sm text-muted">{formatPhoneDisplay(address.phone)}</Text>
      {actions ? <View className="mt-3 flex-row flex-wrap gap-2">{actions}</View> : null}
    </View>
  );

  if (!onPress) return content;
  return (
    <Pressable onPress={onPress} accessibilityRole="button" className="active:opacity-80">
      {content}
    </Pressable>
  );
}
