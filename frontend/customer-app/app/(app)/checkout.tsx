import { formatMoney, normalizePhone, paymentMethodLabel } from "@beverage/api";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useMemo, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";

import { Button } from "@/components/Button";
import { Screen } from "@/components/Screen";
import { EmptyState, ErrorView, LoadingView } from "@/components/StateViews";
import { api, unwrap } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";
import { errorMessage } from "@/lib/errors";
import { isMobileMoney } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/lib/toast";
import type { CheckoutPaymentMethod } from "@/lib/types";

const METHODS: CheckoutPaymentMethod[] = ["CASH", "MPESA", "TIGO_PESA", "AIRTEL_MONEY"];

export default function CheckoutScreen() {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const cartQuery = useCart();
  const addressesQuery = useQuery({
    queryKey: keys.addresses,
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/addresses/", { params: { query: { page_size: 100 } } }))
        .results,
  });

  const addresses = addressesQuery.data ?? [];
  const defaultAddress = addresses.find((item) => item.is_default) ?? addresses[0];
  const [addressId, setAddressId] = useState<number | null>(null);
  const [method, setMethod] = useState<CheckoutPaymentMethod>("CASH");
  const [notes, setNotes] = useState("");
  const [payerPhone, setPayerPhone] = useState(user?.phone ?? "");
  const [submitting, setSubmitting] = useState(false);

  const selectedId = addressId ?? defaultAddress?.id ?? null;
  const cart = cartQuery.data;
  const canSubmit = Boolean(cart && cart.items.length > 0 && selectedId && !submitting);

  const totals = useMemo(() => {
    if (!cart) return null;
    return {
      subtotal: cart.subtotal,
      delivery: cart.delivery_fee,
      total: cart.total,
    };
  }, [cart]);

  const placeOrder = async () => {
    if (!selectedId || !cart) return;
    setSubmitting(true);
    try {
      const order = unwrap(
        await api.POST("/api/v1/orders/", {
          body: {
            address_id: selectedId,
            payment_method: method,
            notes: notes.trim() || null,
            payer_phone: isMobileMoney(method)
              ? normalizePhone(payerPhone) ?? payerPhone
              : null,
          },
        }),
      );
      queryClient.setQueryData(keys.cart, undefined);
      void queryClient.invalidateQueries({ queryKey: keys.cart });
      void queryClient.invalidateQueries({ queryKey: keys.ordersRoot });

      if (isMobileMoney(method)) {
        try {
          await api.POST("/api/v1/orders/{id}/pay/", {
            params: { path: { id: order.id } },
            body: { payer_phone: normalizePhone(payerPhone) ?? payerPhone },
          });
        } catch (error) {
          toast.show(errorMessage(error), "error");
        }
      }
      router.replace(`/order/${order.id}`);
    } catch (error) {
      toast.show(errorMessage(error), "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (cartQuery.isLoading || addressesQuery.isLoading) {
    return (
      <Screen title="Checkout" back>
        <LoadingView />
      </Screen>
    );
  }
  if (cartQuery.isError) {
    return (
      <Screen title="Checkout" back>
        <ErrorView error={cartQuery.error} onRetry={() => void cartQuery.refetch()} />
      </Screen>
    );
  }
  if (!cart || cart.items.length === 0) {
    return (
      <Screen title="Checkout" back>
        <EmptyState title="Your cart is empty" action={<Button title="Go back" onPress={() => router.back()} />} />
      </Screen>
    );
  }

  return (
    <Screen
      title="Checkout"
      back
      footer={
        <Button title="Place order" loading={submitting} disabled={!canSubmit} onPress={() => void placeOrder()} />
      }
    >
      <Text className="mb-2 text-sm font-semibold text-muted">Delivery address</Text>
      {addresses.length === 0 ? (
        <Button title="Add an address" variant="secondary" onPress={() => router.push("/profile/address-form")} />
      ) : (
        addresses.map((address) => (
          <Pressable
            key={address.id}
            onPress={() => setAddressId(address.id)}
            className={`mb-2 rounded-2xl border p-4 ${
              selectedId === address.id ? "border-primary bg-primary/10" : "border-border bg-surface"
            }`}
          >
            <Text className="font-semibold text-foreground">{address.address_name}</Text>
            <Text className="mt-1 text-sm text-muted">{address.address_line}</Text>
          </Pressable>
        ))
      )}

      <Text className="mb-2 mt-6 text-sm font-semibold text-muted">Pay with</Text>
      {METHODS.map((value) => (
        <Pressable
          key={value}
          onPress={() => setMethod(value)}
          className={`mb-2 rounded-2xl border p-4 ${
            method === value ? "border-primary bg-primary/10" : "border-border bg-surface"
          }`}
        >
          <Text className="font-semibold text-foreground">{paymentMethodLabel(value)}</Text>
        </Pressable>
      ))}

      {isMobileMoney(method) ? (
        <View className="mt-2">
          <Text className="mb-1.5 text-sm font-medium text-foreground">Phone for the prompt</Text>
          <TextInput
            value={payerPhone}
            onChangeText={setPayerPhone}
            keyboardType="phone-pad"
            placeholder="0712 345 678"
            placeholderTextColor="#7DA0CA"
            className="rounded-xl border border-border bg-surface px-4 py-3 text-base text-foreground"
          />
        </View>
      ) : null}

      <Text className="mb-1.5 mt-6 text-sm font-medium text-foreground">Notes (optional)</Text>
      <TextInput
        value={notes}
        onChangeText={setNotes}
        multiline
        placeholder="Gate code, landmark…"
        placeholderTextColor="#7DA0CA"
        className="min-h-[80px] rounded-xl border border-border bg-surface px-4 py-3 text-base text-foreground"
      />

      {totals ? (
        <View className="mt-6 rounded-2xl border border-border bg-surface p-4">
          <Row label="Subtotal" value={formatMoney(totals.subtotal)} />
          <Row label="Delivery" value={formatMoney(totals.delivery)} />
          <Row label="Total" value={formatMoney(totals.total)} bold />
        </View>
      ) : null}
    </Screen>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <View className="flex-row items-center justify-between py-1">
      <Text className={`text-sm ${bold ? "font-semibold text-foreground" : "text-muted"}`}>
        {label}
      </Text>
      <Text className={`text-sm ${bold ? "font-bold text-foreground" : "text-foreground"}`}>
        {value}
      </Text>
    </View>
  );
}
