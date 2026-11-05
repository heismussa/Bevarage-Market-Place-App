import { formatMoney } from "@beverage/api";
import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";

import { Button } from "@/components/Button";
import { QuantityStepper } from "@/components/QuantityStepper";
import { RemoteImage } from "@/components/RemoteImage";
import { Screen } from "@/components/Screen";
import { ErrorView, LoadingView } from "@/components/StateViews";
import { Badge } from "@/components/StatusBadge";
import { api, unwrap } from "@/lib/api";
import { useAddToCart } from "@/lib/cart";
import { unitLabel } from "@/lib/format";
import { keys } from "@/lib/query";

export default function ProductScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const productId = Number(id);
  const router = useRouter();
  const [quantity, setQuantity] = useState(1);
  const { addToCart, isAdding, conflictDialog } = useAddToCart();

  const query = useQuery({
    queryKey: keys.product(productId),
    enabled: Number.isFinite(productId),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/products/{id}/", { params: { path: { id: productId } } }),
      ),
  });

  const product = query.data;
  const buyable =
    product?.in_stock && product.availability_status === "AVAILABLE";

  return (
    <Screen
      title={product?.name ?? "Product"}
      back
      footer={
        product && buyable ? (
          <View className="flex-row items-center gap-3">
            <QuantityStepper
              value={quantity}
              onChange={setQuantity}
              max={product.stock_quantity}
              disabled={isAdding}
            />
            <View className="flex-1">
              <Button
                title={`Add · ${formatMoney(product.price)}`}
                loading={isAdding}
                onPress={async () => {
                  const ok = await addToCart(product.id, quantity);
                  if (ok) router.push("/cart");
                }}
              />
            </View>
          </View>
        ) : null
      }
    >
      {conflictDialog}
      {query.isLoading ? <LoadingView /> : null}
      {query.isError ? (
        <ErrorView error={query.error} onRetry={() => void query.refetch()} />
      ) : null}
      {product ? (
        <View>
          <RemoteImage uri={product.image} aspectRatio={1.1} icon="beer-outline" />
          <View className="mt-4 flex-row items-center justify-between">
            <Text className="flex-1 text-2xl font-bold text-foreground">{product.name}</Text>
            <Badge
              label={buyable ? "In stock" : product.availability_status === "UNAVAILABLE" ? "Unavailable" : "Out of stock"}
              tone={buyable ? "success" : "danger"}
            />
          </View>
          <Text className="mt-1 text-sm text-muted">
            {product.store_name} · {unitLabel(product.unit)}
          </Text>
          <Text className="mt-3 text-2xl font-bold text-primary">
            {formatMoney(product.price)}
          </Text>
          {product.description ? (
            <Text className="mt-4 text-base leading-6 text-muted">{product.description}</Text>
          ) : null}
          <Button
            title="View store"
            variant="ghost"
            className="mt-4"
            onPress={() => router.push(`/store/${product.store}`)}
          />
        </View>
      ) : null}
    </Screen>
  );
}
