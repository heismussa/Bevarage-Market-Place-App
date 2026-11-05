import { formatMoney } from "@beverage/api";
import { Ionicons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";

import { unitLabel } from "@/lib/format";
import type { ProductSummary } from "@/lib/types";

import { RemoteImage } from "./RemoteImage";

type ProductCardProps = {
  product: ProductSummary;
  onPress: () => void;
  /** Quick add (quantity 1). Hidden when the product cannot be bought. */
  onAdd?: () => void;
  adding?: boolean;
  showStore?: boolean;
  /** Fixed width for horizontal lists; omit to fill a grid cell. */
  width?: number;
};

export function ProductCard({
  product,
  onPress,
  onAdd,
  adding = false,
  showStore = false,
  width,
}: ProductCardProps) {
  const buyable = product.in_stock && product.availability_status === "AVAILABLE";

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      style={width ? { width } : undefined}
      className={`overflow-hidden rounded-2xl border border-border bg-surface active:opacity-80 ${
        width ? "" : "flex-1"
      }`}
    >
      <RemoteImage
        uri={product.image}
        aspectRatio={1.4}
        icon="beer-outline"
        rounded="rounded-none"
      />
      <View className="p-3">
        <Text numberOfLines={2} className="min-h-[40px] text-sm font-semibold text-foreground">
          {product.name}
        </Text>
        {showStore ? (
          <Text numberOfLines={1} className="mt-0.5 text-xs text-muted">
            {product.store_name}
          </Text>
        ) : null}
        <Text className="mt-0.5 text-xs text-muted">per {unitLabel(product.unit)}</Text>
        <View className="mt-2 flex-row items-center justify-between">
          <Text className="text-base font-bold text-primary">
            {formatMoney(product.price)}
          </Text>
          {buyable && onAdd ? (
            <Pressable
              onPress={onAdd}
              disabled={adding}
              hitSlop={8}
              accessibilityRole="button"
              accessibilityLabel={`Add ${product.name} to cart`}
              className={`h-9 w-9 items-center justify-center rounded-full bg-primary active:opacity-80 ${
                adding ? "opacity-50" : ""
              }`}
            >
              <Ionicons name="add" size={22} color="#021024" />
            </Pressable>
          ) : !buyable ? (
            <Text className="text-xs font-semibold text-danger">
              {product.availability_status === "UNAVAILABLE" ? "Unavailable" : "Out of stock"}
            </Text>
          ) : null}
        </View>
      </View>
    </Pressable>
  );
}
