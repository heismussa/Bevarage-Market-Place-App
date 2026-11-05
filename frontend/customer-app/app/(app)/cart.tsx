import { formatMoney } from "@beverage/api";
import { useRouter } from "expo-router";
import { Text, View } from "react-native";

import { Button } from "@/components/Button";
import { CartLineRow } from "@/components/CartLineRow";
import { Screen } from "@/components/Screen";
import { EmptyState, ErrorView, LoadingView } from "@/components/StateViews";
import { useCart, useCartMutations } from "@/lib/cart";

export default function CartScreen() {
  const router = useRouter();
  const query = useCart();
  const { updateQuantity, removeItem, clearCart } = useCartMutations();
  const cart = query.data;
  const busy = updateQuantity.isPending || removeItem.isPending;

  return (
    <Screen
      title="Cart"
      refreshing={query.isRefetching}
      onRefresh={() => void query.refetch()}
      footer={
        cart && cart.items.length > 0 ? (
          <View>
            <View className="mb-3 flex-row items-center justify-between">
              <Text className="text-sm text-muted">Subtotal</Text>
              <Text className="text-lg font-bold text-foreground">
                {formatMoney(cart.subtotal)}
              </Text>
            </View>
            <Button
              title="Checkout"
              onPress={() => router.push("/checkout")}
              disabled={cart.warnings.length > 0}
            />
            {cart.warnings.length > 0 ? (
              <Text className="mt-2 text-center text-xs text-warning">
                Fix the warnings above before you place the order.
              </Text>
            ) : null}
          </View>
        ) : null
      }
    >
      {query.isLoading ? <LoadingView /> : null}
      {query.isError ? (
        <ErrorView error={query.error} onRetry={() => void query.refetch()} />
      ) : null}
      {cart && cart.items.length === 0 ? (
        <EmptyState
          icon="cart-outline"
          title="Your cart is empty"
          message="Browse a store and add drinks."
          action={<Button title="Find stores" onPress={() => router.push("/")} />}
        />
      ) : null}
      {cart?.items.map((line) => (
        <CartLineRow
          key={line.id}
          line={line}
          warnings={cart.warnings.filter((warning) => warning.item_id === line.id)}
          busy={busy}
          onQuantityChange={(quantity) => {
            if (quantity <= 0) void removeItem.mutateAsync(line.id);
            else void updateQuantity.mutateAsync({ id: line.id, quantity });
          }}
          onRemove={() => void removeItem.mutateAsync(line.id)}
        />
      ))}
      {cart && cart.items.length > 0 ? (
        <Button
          title="Empty cart"
          variant="ghost"
          className="mt-2"
          loading={clearCart.isPending}
          onPress={() => void clearCart.mutateAsync()}
        />
      ) : null}
    </Screen>
  );
}
