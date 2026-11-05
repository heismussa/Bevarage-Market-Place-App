import { formatMoney, paymentMethodLabel, paymentStatusLabel } from "@beverage/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Text, TextInput, View } from "react-native";

import { Button } from "@/components/Button";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { OrderTimeline } from "@/components/OrderTimeline";
import { Screen } from "@/components/Screen";
import { Banner, ErrorView, LoadingView } from "@/components/StateViews";
import { OrderStatusBadge } from "@/components/StatusBadge";
import { api, unwrap } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { isMobileMoney } from "@/lib/format";
import { POLL, keys } from "@/lib/query";
import { useToast } from "@/lib/toast";
import type { Payment } from "@/lib/types";

type PaymentView = Pick<Payment, "payment_method" | "payment_status" | "payer_phone">;

const FINAL = new Set(["COMPLETED", "CANCELLED", "REJECTED"]);
const PAYMENT_POLL_MS = 120_000;

export default function OrderDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const orderId = Number(id);
  const toast = useToast();
  const queryClient = useQueryClient();
  const [cancelOpen, setCancelOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [payTimedOut, setPayTimedOut] = useState(false);
  const payTimedOutRef = useRef(false);

  const query = useQuery({
    queryKey: keys.order(orderId),
    enabled: Number.isFinite(orderId),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/orders/{id}/", { params: { path: { id: orderId } } })),
    refetchInterval: (q) =>
      q.state.data && !FINAL.has(q.state.data.order_status) ? POLL.order : false,
  });

  const paymentQuery = useQuery({
    queryKey: keys.payment(orderId),
    enabled: Number.isFinite(orderId),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/orders/{id}/payment/", { params: { path: { id: orderId } } }),
      ),
    refetchInterval: (q) =>
      q.state.data?.payment_status === "PROCESSING" && !payTimedOutRef.current
        ? POLL.payment
        : false,
  });

  const payment = paymentQuery.data ?? query.data?.payment;

  useEffect(() => {
    if (payment?.payment_status !== "PROCESSING") {
      payTimedOutRef.current = false;
      setPayTimedOut(false);
      return;
    }
    const handle = setTimeout(() => {
      payTimedOutRef.current = true;
      setPayTimedOut(true);
    }, PAYMENT_POLL_MS);
    return () => clearTimeout(handle);
  }, [payment?.id, payment?.payment_status]);

  const pay = useMutation({
    mutationFn: async () =>
      unwrap(
        await api.POST("/api/v1/orders/{id}/pay/", {
          params: { path: { id: orderId } },
          body: { payer_phone: payment?.payer_phone ?? null },
        }),
      ),
    onSuccess: (data) => {
      payTimedOutRef.current = false;
      setPayTimedOut(false);
      void queryClient.invalidateQueries({ queryKey: keys.payment(orderId) });
      toast.show(data.instructions || "Approve the payment on your phone.", "info");
    },
    onError: (error) => toast.show(errorMessage(error), "error"),
  });

  const cancel = useMutation({
    mutationFn: async () =>
      unwrap(
        await api.POST("/api/v1/orders/{id}/cancel/", {
          params: { path: { id: orderId } },
          body: { reason: reason.trim() || null },
        }),
      ),
    onSuccess: (order) => {
      queryClient.setQueryData(keys.order(orderId), order);
      setCancelOpen(false);
      toast.show("Order cancelled.", "success");
    },
    onError: (error) => toast.show(errorMessage(error), "error"),
  });

  const order = query.data;
  const canCancel = order?.allowed_actions?.includes("cancel");

  return (
    <Screen
      title={order ? `#${order.order_number}` : "Order"}
      back
      refreshing={query.isRefetching || paymentQuery.isRefetching}
      onRefresh={() => {
        void query.refetch();
        void paymentQuery.refetch();
      }}
    >
      {query.isLoading ? <LoadingView /> : null}
      {query.isError ? (
        <ErrorView error={query.error} onRetry={() => void query.refetch()} />
      ) : null}
      {order ? (
        <View>
          <View className="mb-4 flex-row items-center justify-between">
            <Text className="text-lg font-semibold text-foreground">{order.store.store_name}</Text>
            <OrderStatusBadge status={order.order_status} />
          </View>

          {order.items.map((item) => (
            <View key={item.id} className="mb-2 flex-row justify-between">
              <Text className="flex-1 text-sm text-foreground">
                {item.quantity} × {item.product_name}
              </Text>
              <Text className="text-sm text-foreground">{formatMoney(item.subtotal)}</Text>
            </View>
          ))}

          <View className="mt-4 rounded-2xl border border-border bg-surface p-4">
            <Row label="Subtotal" value={formatMoney(order.subtotal_amount)} />
            <Row label="Delivery" value={formatMoney(order.delivery_fee)} />
            <Row label="Total" value={formatMoney(order.total_amount)} />
            {payment ? (
              <Row
                label="Payment"
                value={`${paymentMethodLabel(payment.payment_method)} · ${paymentStatusLabel(
                  payment.payment_status,
                  { isCash: payment.payment_method === "CASH" },
                )}`}
              />
            ) : null}
          </View>

          {payment ? (
            <PaymentPanel
              payment={payment}
              timedOut={payTimedOut}
              paying={pay.isPending}
              onPay={() => void pay.mutateAsync()}
            />
          ) : null}

          {order.status_history?.length ? (
            <View className="mt-6">
              <Text className="mb-2 text-sm font-semibold text-muted">Timeline</Text>
              <OrderTimeline history={order.status_history} />
            </View>
          ) : null}

          {canCancel ? (
            <Button
              title="Cancel order"
              variant="danger"
              className="mt-3"
              onPress={() => setCancelOpen(true)}
            />
          ) : null}
        </View>
      ) : null}

      <ConfirmDialog
        visible={cancelOpen}
        title="Cancel this order?"
        message="Stock will be returned to the store. You can add a reason."
        confirmLabel="Cancel order"
        loading={cancel.isPending}
        onCancel={() => setCancelOpen(false)}
        onConfirm={() => void cancel.mutateAsync()}
      >
        <TextInput
          value={reason}
          onChangeText={setReason}
          placeholder="Reason (optional)"
          placeholderTextColor="#7DA0CA"
          className="mt-3 rounded-xl border border-border bg-background px-4 py-3 text-base text-foreground"
        />
      </ConfirmDialog>
    </Screen>
  );
}

function PaymentPanel({
  payment,
  timedOut,
  paying,
  onPay,
}: {
  payment: PaymentView;
  timedOut: boolean;
  paying: boolean;
  onPay: () => void;
}) {
  const cash = payment.payment_method === "CASH";
  const mobile = isMobileMoney(payment.payment_method);
  const status = payment.payment_status;

  if (cash) {
    return (
      <View className="mt-4">
        <Banner
          tone="info"
          message={
            status === "SUCCESS"
              ? "Paid."
              : "Pay on delivery. You will not be charged in the app."
          }
        />
      </View>
    );
  }

  if (status === "SUCCESS") {
    return (
      <View className="mt-4">
        <Banner tone="info" message="Paid." />
      </View>
    );
  }

  if (status === "CANCELLED") {
    return (
      <View className="mt-4">
        <Banner tone="info" message="Not charged." />
      </View>
    );
  }

  if (status === "PROCESSING") {
    return (
      <View className="mt-4">
        <Banner
          tone={timedOut ? "warning" : "info"}
          message={
            timedOut
              ? "Still waiting for approval. Pull to refresh, or we will update this order when the payment finishes."
              : "Waiting for approval on your phone."
          }
        />
      </View>
    );
  }

  if (mobile && (status === "PENDING" || status === "FAILED")) {
    return (
      <View className="mt-4">
        {status === "FAILED" ? (
          <Banner tone="error" message="Payment failed. You can try again. You were not charged." />
        ) : null}
        <Button
          title={status === "FAILED" ? "Try payment again" : "Pay now"}
          className={status === "FAILED" ? "mt-3" : ""}
          loading={paying}
          onPress={onPay}
        />
      </View>
    );
  }

  return null;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View className="flex-row items-center justify-between py-1">
      <Text className="text-sm text-muted">{label}</Text>
      <Text className="text-sm font-semibold text-foreground">{value}</Text>
    </View>
  );
}
