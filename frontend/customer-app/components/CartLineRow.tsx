import { formatMoney } from "@beverage/api";
import { Ionicons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";

import { unitLabel } from "@/lib/format";
import type { CartLine, CartWarning } from "@/lib/types";

import { QuantityStepper } from "./QuantityStepper";
import { RemoteImage } from "./RemoteImage";

type CartLineRowProps = {
  line: CartLine;
  warnings: CartWarning[];
  busy: boolean;
  onQuantityChange: (quantity: number) => void;
  onRemove: () => void;
};

export function CartLineRow({
  line,
  warnings,
  busy,
  onQuantityChange,
  onRemove,
}: CartLineRowProps) {
  return (
    <View
      className={`mb-3 rounded-2xl border bg-surface p-3 ${
        line.counted_in_total ? "border-border" : "border-warning"
      }`}
    >
      <View className="flex-row">
        <RemoteImage uri={line.image} size={64} icon="beer-outline" />
        <View className="ml-3 flex-1">
          <View className="flex-row items-start justify-between">
            <Text numberOfLines={2} className="mr-2 flex-1 text-base font-semibold text-foreground">
              {line.name}
            </Text>
            <Pressable
              onPress={onRemove}
              disabled={busy}
              hitSlop={10}
              accessibilityRole="button"
              accessibilityLabel={`Remove ${line.name}`}
            >
              <Ionicons name="trash-outline" size={20} color="#F87171" />
            </Pressable>
          </View>
          <Text className="text-xs text-muted">
            {formatMoney(line.unit_price)} per {unitLabel(line.unit)}
          </Text>
          {line.price_changed ? (
            <Text className="mt-0.5 text-xs text-warning">
              Price changed since you added it (was {formatMoney(line.price_when_added)})
            </Text>
          ) : null}
        </View>
      </View>

      <View className="mt-3 flex-row items-center justify-between">
        <QuantityStepper
          value={line.quantity}
          min={0}
          max={line.max_available > 0 ? line.max_available : undefined}
          disabled={busy}
          onChange={onQuantityChange}
        />
        <Text className="text-base font-bold text-foreground">
          {formatMoney(line.line_total)}
        </Text>
      </View>

      {!line.counted_in_total ? (
        <Text className="mt-2 text-xs text-warning">
          Not included in the total until it is available again.
        </Text>
      ) : null}
      {warnings.map((warning) => (
        <Text key={`${warning.code}-${warning.message}`} className="mt-1 text-xs text-warning">
          {warning.message}
        </Text>
      ))}
    </View>
  );
}
