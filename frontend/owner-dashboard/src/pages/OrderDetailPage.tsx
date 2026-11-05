import {
  ApiError,
  formatDateTime,
  formatMoney,
  formatPhoneDisplay,
  orderStatusLabel,
  paymentMethodLabel,
} from "@beverage/api";
import { ArrowLeft, MapPin, Phone, User } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router";

import {
  ErrorState,
  OrderStatusBadge,
  PageHeader,
  PaymentStatusBadge,
} from "@/components/common";
import { ReasonDialog } from "@/components/ReasonDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { errorMessage } from "@/lib/api";
import { useOrder, useTransitionOrder } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import type { OrderAction } from "@/lib/types";

const ACTION_LABELS: Record<OrderAction, string> = {
  accept: "Accept order",
  reject: "Reject order",
  prepare: "Start preparing",
  ready: "Mark ready",
  complete: "Complete order",
  cancel: "Cancel order",
};

const ACTION_DONE: Record<OrderAction, string> = {
  accept: "Order accepted.",
  reject: "Order rejected.",
  prepare: "Order is being prepared.",
  ready: "Order marked ready.",
  complete: "Order completed.",
  cancel: "Order cancelled.",
};

/** Actions that need a customer-facing reason. */
const NEEDS_REASON: OrderAction[] = ["reject", "cancel"];

export default function OrderDetailPage() {
  const params = useParams();
  const orderId = Number(params.id);
  const toast = useToast();
  const query = useOrder(orderId);
  const transition = useTransitionOrder(orderId);
  const [reasonAction, setReasonAction] = useState<OrderAction | null>(null);
  const [reasonError, setReasonError] = useState<string | null>(null);

  const run = async (action: OrderAction, reason?: string) => {
    try {
      await transition.mutateAsync({ action, reason });
      toast.success(ACTION_DONE[action]);
      setReasonAction(null);
      setReasonError(null);
    } catch (error) {
      const message = errorMessage(error);
      if (error instanceof ApiError && error.code === "INVALID_TRANSITION") {
        // The order moved under us; reload the real allowed actions.
        void query.refetch();
        setReasonAction(null);
      }
      if (reasonAction) setReasonError(message);
      toast.error(message);
    }
  };

  if (query.isError) {
    return (
      <>
        <BackLink />
        <Card>
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        </Card>
      </>
    );
  }

  const order = query.data;
  if (!order) {
    return (
      <>
        <BackLink />
        <Skeleton className="mb-4 h-16" />
        <div className="grid gap-4 lg:grid-cols-3">
          <Skeleton className="h-72 lg:col-span-2" />
          <Skeleton className="h-72" />
        </div>
      </>
    );
  }

  const isCash = order.payment?.payment_method === "CASH";

  return (
    <>
      <BackLink />
      <PageHeader
        title={`Order ${order.order_number}`}
        description={`Placed ${formatDateTime(order.ordered_at)}`}
        actions={
          <>
            <OrderStatusBadge status={order.order_status} />
            <PaymentStatusBadge status={order.payment_status} isCash={isCash} />
          </>
        }
      />

      {order.status_reason ? (
        <div className="mb-4 rounded-xl border border-border bg-surface-muted px-4 py-3 text-sm">
          <span className="font-semibold">Reason: </span>
          {order.status_reason}
        </div>
      ) : null}

      {order.allowed_actions.length > 0 ? (
        <Card className="mb-4">
          <CardContent className="flex flex-wrap items-center gap-3 pt-5">
            <p className="mr-2 text-sm font-medium text-muted">Next step</p>
            {order.allowed_actions.map((action) => {
              const destructive = NEEDS_REASON.includes(action);
              return (
                <Button
                  key={action}
                  variant={destructive ? "destructive-outline" : "default"}
                  disabled={transition.isPending}
                  loading={
                    transition.isPending &&
                    transition.variables?.action === action &&
                    !destructive
                  }
                  onClick={() => {
                    if (destructive) {
                      setReasonError(null);
                      setReasonAction(action);
                    } else {
                      void run(action);
                    }
                  }}
                >
                  {ACTION_LABELS[action]}
                </Button>
              );
            })}
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Items</CardTitle>
            </CardHeader>
            <CardContent className="px-0 pb-0">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Product</TableHead>
                    <TableHead className="text-right">Qty</TableHead>
                    <TableHead className="text-right">Unit price</TableHead>
                    <TableHead className="text-right">Subtotal</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {order.items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <p className="font-medium">{item.product_name}</p>
                        <p className="text-xs text-muted capitalize">
                          {item.unit.toLowerCase()}
                        </p>
                      </TableCell>
                      <TableCell className="text-right">{item.quantity}</TableCell>
                      <TableCell className="text-right">{formatMoney(item.unit_price)}</TableCell>
                      <TableCell className="text-right font-medium">
                        {formatMoney(item.subtotal)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <dl className="space-y-1.5 border-t border-border p-5 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted">Subtotal</dt>
                  <dd>{formatMoney(order.subtotal_amount)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted">Delivery fee</dt>
                  <dd>{formatMoney(order.delivery_fee)}</dd>
                </div>
                <div className="flex justify-between text-base font-bold">
                  <dt>Total</dt>
                  <dd>{formatMoney(order.total_amount)}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Status history</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="space-y-4">
                {order.status_history.map((entry, index) => (
                  <li key={`${entry.changed_at}-${index}`} className="flex gap-3">
                    <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-primary" />
                    <div className="text-sm">
                      <p className="font-medium">
                        {orderStatusLabel(entry.status)}
                        {entry.changed_by_role ? (
                          <span className="ml-2 text-xs font-normal text-muted capitalize">
                            by {entry.changed_by_role.toLowerCase().replace("_", " ")}
                          </span>
                        ) : (
                          <span className="ml-2 text-xs font-normal text-muted">by system</span>
                        )}
                      </p>
                      <p className="text-xs text-muted">{formatDateTime(entry.changed_at)}</p>
                      {entry.notes ? <p className="mt-0.5 text-muted">{entry.notes}</p> : null}
                    </div>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Customer</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p className="flex items-center gap-2">
                <User size={16} className="text-muted" /> {order.customer.full_name}
              </p>
              <p className="flex items-center gap-2">
                <Phone size={16} className="text-muted" />
                <a className="text-primary hover:underline" href={`tel:${order.customer.phone}`}>
                  {formatPhoneDisplay(order.customer.phone)}
                </a>
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Delivery</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p className="flex items-start gap-2">
                <MapPin size={16} className="mt-0.5 shrink-0 text-muted" />
                {order.delivery_address}
              </p>
              <p className="flex items-center gap-2">
                <Phone size={16} className="text-muted" />
                {formatPhoneDisplay(order.delivery_phone)}
              </p>
              {order.delivery_latitude && order.delivery_longitude ? (
                <a
                  className="inline-block text-primary hover:underline"
                  target="_blank"
                  rel="noreferrer"
                  href={`https://www.google.com/maps?q=${order.delivery_latitude},${order.delivery_longitude}`}
                >
                  Open in maps
                </a>
              ) : null}
              {order.notes ? (
                <p className="rounded-lg bg-surface-muted p-2 text-muted">
                  <span className="font-medium text-foreground">Note: </span>
                  {order.notes}
                </p>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Payment</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {order.payment ? (
                <>
                  <div className="flex justify-between">
                    <span className="text-muted">Method</span>
                    <span>{paymentMethodLabel(order.payment.payment_method)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Status</span>
                    <PaymentStatusBadge status={order.payment.payment_status} isCash={isCash} />
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Amount</span>
                    <span>{formatMoney(order.payment.amount)}</span>
                  </div>
                  {order.payment.payer_phone ? (
                    <div className="flex justify-between">
                      <span className="text-muted">Payer</span>
                      <span>{formatPhoneDisplay(order.payment.payer_phone)}</span>
                    </div>
                  ) : null}
                </>
              ) : (
                <p className="text-muted">No payment recorded.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <ReasonDialog
        open={reasonAction !== null}
        title={reasonAction === "reject" ? "Reject this order?" : "Cancel this order?"}
        confirmLabel={reasonAction === "reject" ? "Reject order" : "Cancel order"}
        loading={transition.isPending}
        serverError={reasonError}
        onClose={() => setReasonAction(null)}
        onConfirm={(reason) => {
          if (reasonAction) void run(reasonAction, reason);
        }}
      />
    </>
  );
}

function BackLink() {
  return (
    <Link
      to="/orders"
      className="mb-3 inline-flex items-center gap-1 text-sm font-medium text-muted hover:text-foreground"
    >
      <ArrowLeft size={14} /> Back to orders
    </Link>
  );
}
